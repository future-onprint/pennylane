"""Pennylane Product sync — push on save, pull via changelog."""

import frappe
import frappe.utils

from pennylane.client.base import PennylaneClient
from pennylane.client.products import (
	create_product,
	get_changelog,
	get_product,
	list_products,
	update_product,
)
from pennylane.mappers.product import from_pennylane, to_pennylane
from pennylane.sync.utils import enqueue_sync, is_integration_enabled, write_log

_SYNC_FLAG = "pennylane_sync_source"


# ------------------------------------------------------------------
# Doc event
# ------------------------------------------------------------------


def on_product_save(doc, method=None):
	if getattr(doc.flags, _SYNC_FLAG, None) == "pennylane":
		return
	if not is_integration_enabled():
		return
	enqueue_sync("pennylane.sync.product.push_product", doc_name=doc.name)


# ------------------------------------------------------------------
# Push
# ------------------------------------------------------------------


def push_product(doc_name: str):
	client = PennylaneClient.from_settings()
	payload = to_pennylane(doc_name)
	existing_id = frappe.db.get_value("Pennylane Product", doc_name, "pennylane_id")

	try:
		if existing_id:
			resp = update_product(client, existing_id, payload)
			operation = "update"
		else:
			resp = create_product(client, payload)
			operation = "create"

		frappe.db.set_value("Pennylane Product", doc_name, {
			"pennylane_id": resp.get("id"),
			"sync_status": "Synced",
			"last_synced_at": frappe.utils.now_datetime(),
		})
		write_log(direction="push", resource_type="product", operation=operation,
			status="Success", frappe_doctype="Pennylane Product", frappe_docname=doc_name,
			pennylane_id=resp.get("id"), request_payload=payload, response_payload=resp)

	except Exception as exc:
		frappe.db.set_value("Pennylane Product", doc_name, "sync_status", "Failed")
		write_log(direction="push", resource_type="product",
			operation="create" if not existing_id else "update",
			status="Failed", frappe_doctype="Pennylane Product", frappe_docname=doc_name,
			request_payload=payload, error_message=str(exc),
			http_status_code=getattr(exc, "status_code", None))
		frappe.log_error(str(exc), f"Pennylane push_product: {doc_name}")
		raise


def ensure_product_synced(doc_name: str) -> int | None:
	"""Ensure a Pennylane Product has a pennylane_id — push synchronously if not."""
	pl_id = frappe.db.get_value("Pennylane Product", doc_name, "pennylane_id")
	if pl_id:
		return pl_id
	push_product(doc_name)
	return frappe.db.get_value("Pennylane Product", doc_name, "pennylane_id")


# ------------------------------------------------------------------
# Pull
# ------------------------------------------------------------------


def pull_products():
	if not is_integration_enabled():
		return

	settings = frappe.get_cached_doc("Pennylane Settings")
	client = PennylaneClient.from_settings()
	cursor = settings.product_changelog_cursor or None

	resp = get_changelog(client, cursor=cursor)
	items = resp.get("items", [])

	for change in items:
		pl_id = change["resource_id"]
		if change["operation"] == "delete":
			_handle_delete(pl_id)
			continue
		try:
			_upsert(get_product(client, pl_id))
		except Exception as exc:
			write_log(direction="pull", resource_type="product", operation=change["operation"],
				status="Failed", pennylane_id=pl_id, error_message=str(exc))
			frappe.log_error(str(exc), f"Pennylane pull_products id={pl_id}")

	next_cursor = resp.get("next_cursor") if resp.get("has_more") else (items[-1].get("id") if items else cursor)
	frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "product_changelog_cursor", next_cursor)


def full_sync_products():
	"""Pull all products from the list endpoint (force full sync)."""
	if not is_integration_enabled():
		return
	client = PennylaneClient.from_settings()
	for pl_product in list_products(client):
		try:
			_upsert(pl_product)
		except Exception as exc:
			frappe.log_error(str(exc), f"Pennylane full_sync_products id={pl_product.get('id')}")
	frappe.db.set_value("Pennylane Settings", "Pennylane Settings", "product_changelog_cursor", None)


def _upsert(pl_data: dict):
	pl_id = pl_data.get("id")
	fields = from_pennylane(pl_data)
	existing = frappe.db.get_value("Pennylane Product", {"pennylane_id": pl_id}, "name")

	if existing:
		doc = frappe.get_doc("Pennylane Product", existing)
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update(fields)
		doc.sync_status = "Synced"
		doc.last_synced_at = frappe.utils.now_datetime()
		doc.save(ignore_permissions=True)
		write_log(direction="pull", resource_type="product", operation="update", status="Success",
			frappe_doctype="Pennylane Product", frappe_docname=existing, pennylane_id=pl_id)
	else:
		doc = frappe.new_doc("Pennylane Product")
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update(fields)
		doc.sync_status = "Synced"
		doc.last_synced_at = frappe.utils.now_datetime()
		doc.insert(ignore_permissions=True)
		write_log(direction="pull", resource_type="product", operation="create", status="Success",
			frappe_doctype="Pennylane Product", frappe_docname=doc.name, pennylane_id=pl_id)


def _handle_delete(pl_id: int):
	existing = frappe.db.get_value("Pennylane Product", {"pennylane_id": pl_id}, "name")
	if existing:
		frappe.db.set_value("Pennylane Product", existing, "sync_status", "Failed")
	write_log(direction="pull", resource_type="product", operation="delete",
		status="Success", pennylane_id=pl_id)
