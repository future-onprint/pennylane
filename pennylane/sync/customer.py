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
from pennylane.sync.utils import enqueue_sync, is_integration_enabled, write_log

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
	enqueue_sync(
		"pennylane.sync.customer.push_customer",
		doc_name=doc.name,
	)


# ------------------------------------------------------------------
# Push (background job)
# ------------------------------------------------------------------


def push_customer(doc_name: str):
	"""Create or update the customer in Pennylane, update sync_status."""
	client = PennylaneClient.from_settings()
	payload = to_pennylane(doc_name)

	existing_id = frappe.db.get_value("Pennylane Customer", doc_name, "pennylane_id")

	try:
		if existing_id:
			resp = update_customer(client, existing_id, payload)
			operation = "update"
		else:
			resp = create_customer(client, payload)
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
		frappe.log_error(str(exc), f"Pennylane push_customer: {doc_name}")
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

	resp = get_changelog(client, cursor=cursor)
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
	next_cursor = resp.get("next_cursor") if resp.get("has_more") else (items[-1].get("id") if items else cursor)
	frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "customer_changelog_cursor", next_cursor)


def _upsert(pl_data: dict, client: PennylaneClient = None):
	pl_id = pl_data.get("id")
	fields = from_pennylane(pl_data)

	existing = frappe.db.get_value("Pennylane Customer", {"pennylane_id": pl_id}, "name")

	if existing:
		doc = frappe.get_doc("Pennylane Customer", existing)
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update(fields)
		doc.sync_status = "Synced"
		doc.last_synced_at = frappe.utils.now_datetime()
		doc.save(ignore_permissions=True)
		write_log(
			direction="pull", resource_type="customer", operation="update", status="Success",
			frappe_doctype="Pennylane Customer", frappe_docname=existing, pennylane_id=pl_id,
		)
	else:
		doc = frappe.new_doc("Pennylane Customer")
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update(fields)
		doc.sync_status = "Synced"
		doc.last_synced_at = frappe.utils.now_datetime()
		doc.insert(ignore_permissions=True)
		write_log(
			direction="pull", resource_type="customer", operation="create", status="Success",
			frappe_doctype="Pennylane Customer", frappe_docname=doc.name, pennylane_id=pl_id,
		)

	# Sync contacts if we have a Pennylane ID and a client is available
	if pl_id and client is not None:
		_sync_contacts(doc, client, pl_id)


def _handle_delete(pl_id: int):
	existing = frappe.db.get_value("Pennylane Customer", {"pennylane_id": pl_id}, "name")
	if existing:
		frappe.db.set_value("Pennylane Customer", existing, "sync_status", "Failed")
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


def full_sync_customers():
	"""Pull all customers from the list endpoint (force full sync)."""
	from pennylane.client.customers import list_customers

	if not is_integration_enabled():
		return
	client = PennylaneClient.from_settings()
	for pl_customer in list_customers(client):
		try:
			_upsert(pl_customer, client)
		except Exception as exc:
			frappe.log_error(str(exc), f"Pennylane full_sync_customers id={pl_customer.get('id')}")
	frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "customer_changelog_cursor", None)
