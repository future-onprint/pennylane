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
		pl_id = change["resource_id"]
		op = change["operation"]

		if op == "delete":
			_handle_delete(pl_id)
			continue

		try:
			pl_data = get_customer(client, pl_id)
			_upsert(pl_data)
		except Exception as exc:
			write_log(
				direction="pull",
				resource_type="customer",
				operation=op,
				status="Failed",
				pennylane_id=pl_id,
				error_message=str(exc),
			)
			frappe.log_error(str(exc), f"Pennylane pull_customers id={pl_id}")

	# Advance cursor for next run
	next_cursor = resp.get("next_cursor") if resp.get("has_more") else (items[-1].get("id") if items else cursor)
	frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "customer_changelog_cursor", next_cursor)


def _upsert(pl_data: dict):
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


def _handle_delete(pl_id: int):
	existing = frappe.db.get_value("Pennylane Customer", {"pennylane_id": pl_id}, "name")
	if existing:
		frappe.db.set_value("Pennylane Customer", existing, "sync_status", "Failed")
	write_log(
		direction="pull", resource_type="customer", operation="delete", status="Success",
		pennylane_id=pl_id,
	)
