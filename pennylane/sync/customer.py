"""
Pennylane Customer sync.

Push:  Pennylane Customer (Frappe) → Pennylane API  on after_insert / on_update
Pull:  Pennylane API changelog → Pennylane Customer (Frappe)  every hour
"""

import frappe
import frappe.utils

from pennylane.client.base import PennylaneClient
from pennylane.client.customers import (
	create_customer,
	get_changelog,
	get_customer,
	get_customer_contacts,
	update_customer,
)
from pennylane.mappers.customer import from_pennylane, to_pennylane
from pennylane.mappers import parse_pennylane_dt
from pennylane.sync.utils import enqueue_sync, is_integration_enabled, notify_full_sync_complete, set_creation, write_log

_SYNC_FLAG = "pennylane_sync_source"


# ------------------------------------------------------------------
# Doc event hooks (wired in hooks.py)
# ------------------------------------------------------------------


def on_customer_save(doc, method=None):
	"""Triggered on after_insert and on_update of Pennylane Customer."""
	if getattr(doc.flags, _SYNC_FLAG, None) == "pennylane":
		return  # pulled from API — don't re-push
	if not is_integration_enabled():
		return
	operation = "create" if not frappe.db.get_value("Pennylane Customer", doc.name, "pennylane_id") else "update"
	enqueue_sync("customer", "Pennylane Customer", doc.name, operation=operation)


# ------------------------------------------------------------------
# Push (background job)
# ------------------------------------------------------------------


def push_customer(doc_name: str):
	"""Create or update the customer in Pennylane, update sync_status."""
	client = PennylaneClient.from_settings()
	payload = to_pennylane(doc_name)

	row = frappe.db.get_value("Pennylane Customer", doc_name, ["pennylane_id", "customer_type"], as_dict=True) or {}
	existing_id = row.get("pennylane_id")
	customer_type = row.get("customer_type") or "company"

	try:
		if existing_id:
			resp = update_customer(client, existing_id, payload, customer_type=customer_type)
			operation = "update"
		else:
			resp = create_customer(client, payload, customer_type=customer_type)
			operation = "create"

		frappe.db.set_value(
			"Pennylane Customer",
			doc_name,
			{
				"pennylane_id": resp.get("id"),
				"sync_status": "Synced",
				"last_synced_at": frappe.utils.now_datetime(),
			},
		)

		write_log(
			direction="push",
			resource_type="customer",
			operation=operation,
			status="Success",
			frappe_doctype="Pennylane Customer",
			frappe_docname=doc_name,
			pennylane_id=resp.get("id"),
			request_payload=payload,
			response_payload=resp,
		)

	except Exception as exc:
		frappe.db.set_value("Pennylane Customer", doc_name, "sync_status", "Failed")
		write_log(
			direction="push",
			resource_type="customer",
			operation="create" if not existing_id else "update",
			status="Failed",
			frappe_doctype="Pennylane Customer",
			frappe_docname=doc_name,
			request_payload=payload,
			error_message=str(exc),
			http_status_code=getattr(exc, "status_code", None),
		)
		frappe.log_error(
			f"customer_type={customer_type} existing_id={existing_id}\n{str(exc)}",
			f"Pennylane push_customer: {doc_name}",
		)
		raise


# ------------------------------------------------------------------
# Pull (scheduled — hourly)
# ------------------------------------------------------------------


def pull_customers():
	"""Fetch customer changes from Pennylane changelog and upsert local docs."""
	if not is_integration_enabled():
		return

	client = PennylaneClient.from_settings()
	settings = frappe.get_cached_doc("Pennylane Settings")
	cursor = settings.customer_changelog_cursor or None
	start_date = f"{settings.sync_from_date}T00:00:00Z" if (not cursor and settings.sync_from_date) else None

	try:
		resp = get_changelog(client, cursor=cursor, start_date=start_date)
	except Exception as exc:
		if "cursor" in str(exc).lower():
			frappe.log_error(str(exc), "Pennylane pull_customers: invalid cursor — resetting")
			frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "customer_changelog_cursor", None)
			frappe.db.commit()
			return  # Let next scheduled run start fresh from the beginning
		else:
			raise

	items = resp.get("items", [])

	for change in items:
		try:
			pl_id = change["id"]
			op = change["operation"]
			if op == "delete":
				_handle_delete(pl_id)
				continue
			pl_data = get_customer(client, pl_id)
			_upsert(pl_data, client)
		except Exception as exc:
			write_log(
				direction="pull",
				resource_type="customer",
				operation=change.get("operation", "unknown"),
				status="Failed",
				pennylane_id=change.get("id"),
				error_message=str(exc),
			)
			frappe.log_error(str(exc), f"Pennylane pull_customers id={change.get('id')}")

	# Advance cursor for next run
	next_cursor = resp.get("next_cursor") or cursor
	frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "customer_changelog_cursor", next_cursor)
	frappe.db.commit()


def _upsert(pl_data: dict, client: PennylaneClient = None, write_sync_log: bool = True):
	pl_id = pl_data.get("id")
	fields = from_pennylane(pl_data)

	existing = frappe.db.get_value("Pennylane Customer", {"pennylane_id": pl_id}, "name")

	pl_created_at = parse_pennylane_dt(pl_data.get("created_at"))

	if existing:
		doc = frappe.get_doc("Pennylane Customer", existing)
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update(fields)
		doc.sync_status = "Synced"
		doc.last_synced_at = frappe.utils.now_datetime()
		doc.save(ignore_permissions=True)
		if write_sync_log:
			write_log(
				direction="pull", resource_type="customer", operation="update", status="Success",
				frappe_doctype="Pennylane Customer", frappe_docname=existing, pennylane_id=pl_id,
				response_payload=pl_data,
			)
	else:
		doc = frappe.new_doc("Pennylane Customer")
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update(fields)
		doc.sync_status = "Synced"
		doc.last_synced_at = frappe.utils.now_datetime()
		doc.insert(ignore_permissions=True)
		if pl_created_at:
			set_creation("Pennylane Customer", doc.name, pl_created_at)
		if write_sync_log:
			write_log(
				direction="pull", resource_type="customer", operation="create", status="Success",
				frappe_doctype="Pennylane Customer", frappe_docname=doc.name, pennylane_id=pl_id,
				response_payload=pl_data,
			)

	# Sync contacts if we have a Pennylane ID and a client is available
	if pl_id and client is not None:
		_sync_contacts(doc, client, pl_id)

	# Update creation AFTER all doc.save() calls to avoid Frappe detecting a mismatch
	# between the in-memory doc and the DB snapshot on the next save
	if pl_created_at and existing:
		set_creation("Pennylane Customer", existing, pl_created_at)


def _handle_delete(pl_id: int):
	existing = frappe.db.get_value("Pennylane Customer", {"pennylane_id": pl_id}, "name")
	if existing:
		frappe.db.set_value("Pennylane Customer", existing, "sync_status", "Deleted")
	write_log(
		direction="pull", resource_type="customer", operation="delete", status="Success",
		pennylane_id=pl_id,
	)


def _sync_contacts(doc, client: PennylaneClient, pl_customer_id: int) -> None:
	"""Fetch contacts from Pennylane and replace the child table rows."""
	try:
		contacts = get_customer_contacts(client, pl_customer_id)
	except Exception as exc:
		frappe.log_error(str(exc), f"Pennylane _sync_contacts id={pl_customer_id}")
		return

	rows = []
	for c in contacts:
		rows.append({
			"pennylane_id": c.get("id"),
			"first_name": c.get("first_name"),
			"last_name": c.get("last_name"),
			"role": c.get("role"),
			"email": c.get("email"),
			"telephone_number": c.get("telephone_number"),
			"mobile_number": c.get("mobile_number"),
		})

	doc.flags[_SYNC_FLAG] = "pennylane"
	doc.set("contacts", rows)
	doc.save(ignore_permissions=True)


def pull_single(pl_id: int) -> None:
	"""Pull a single customer from Pennylane by its Pennylane ID and upsert locally."""
	if not is_integration_enabled():
		return
	client = PennylaneClient.from_settings()
	try:
		_upsert(get_customer(client, pl_id), client)
	except Exception as exc:
		write_log(
			direction="pull", resource_type="customer", operation="sync",
			status="Failed", pennylane_id=pl_id, error_message=str(exc),
		)
		frappe.log_error(str(exc), f"Pennylane pull_single customer id={pl_id}")
		raise


def full_sync_customers():
	"""Pull all customers from the list endpoint (force full sync)."""
	from pennylane.client.customers import list_customers

	if not is_integration_enabled():
		return

	lock_key = "pennylane_full_sync_customers"
	if not frappe.cache().set(lock_key, "1", nx=True, ex=3600):
		frappe.log_error("Full sync already running — skipping.", "Pennylane full_sync_customers")
		return

	client = PennylaneClient.from_settings()
	ok = errors = 0
	try:
		for pl_customer in list_customers(client):
			try:
				_upsert(pl_customer, client, write_sync_log=False)
				ok += 1
			except Exception as exc:
				errors += 1
				frappe.log_error(str(exc), f"Pennylane full_sync_customers id={pl_customer.get('id')}")
			finally:
				frappe.db.commit()
		frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "customer_changelog_cursor", None)
		write_log(
			direction="pull", resource_type="customer", operation="full_sync",
			status="Success" if not errors else "Failed",
			error_message=f"{ok} imported, {errors} errors" if errors else f"{ok} imported",
		)
		notify_full_sync_complete("customer", ok, errors)
		frappe.db.commit()
	finally:
		frappe.cache().delete(lock_key)
