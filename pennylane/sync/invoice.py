"""Pennylane Customer Invoice sync — push on save/submit, pull via changelog."""

import frappe
import frappe.utils
from pennylane.utils.pdf import attach_pdf

from pennylane.client.base import PennylaneClient
from pennylane.client.invoices import (
	create_invoice,
	get_changelog,
	get_invoice,
	list_invoices,
	update_invoice,
)
from pennylane.mappers.invoice import from_pennylane, to_pennylane
from pennylane.sync.utils import enqueue_sync, is_integration_enabled, write_log

_SYNC_FLAG = "pennylane_sync_source"


# ------------------------------------------------------------------
# Doc events
# ------------------------------------------------------------------


def on_invoice_save(doc, method=None):
	"""Fired on after_insert / on_update — only for draft (docstatus=0) docs."""
	if getattr(doc.flags, _SYNC_FLAG, None) == "pennylane":
		return
	if not is_integration_enabled():
		return
	if doc.docstatus != 0:
		return
	settings = frappe.get_cached_doc("Pennylane Settings")
	if not settings.sync_invoices:
		return
	enqueue_sync("pennylane.sync.invoice.push_invoice", doc_name=doc.name, finalized=False)


def on_invoice_submit(doc, method=None):
	"""Fired on on_submit — pushes the invoice as finalized to Pennylane."""
	if getattr(doc.flags, _SYNC_FLAG, None) == "pennylane":
		return
	if not is_integration_enabled():
		return
	settings = frappe.get_cached_doc("Pennylane Settings")
	if not settings.sync_invoices:
		return
	enqueue_sync("pennylane.sync.invoice.push_invoice", doc_name=doc.name, finalized=True)


def on_invoice_cancel(doc, method=None):
	"""Fired on on_cancel — updates sync_status locally (Pennylane cancellation is manual)."""
	if getattr(doc.flags, _SYNC_FLAG, None) == "pennylane":
		return
	frappe.db.set_value("Pennylane Customer Invoice", doc.name, "sync_status", "Failed")
	write_log(
		direction="push", resource_type="customer_invoice", operation="cancel",
		status="Info", frappe_doctype="Pennylane Customer Invoice", frappe_docname=doc.name,
		pennylane_id=doc.pennylane_id,
		error_message="Invoice cancelled in Frappe. Manual action may be required in Pennylane.",
	)


# ------------------------------------------------------------------
# Push
# ------------------------------------------------------------------


def push_invoice(doc_name: str, finalized: bool = False):
	doc = frappe.get_doc("Pennylane Customer Invoice", doc_name)

	_ensure_customer(doc.customer)

	client = PennylaneClient.from_settings()
	payload = to_pennylane(doc_name, finalized=finalized)
	existing_id = doc.pennylane_id

	try:
		if existing_id:
			resp = update_invoice(client, existing_id, payload)
			operation = "update"
		else:
			resp = create_invoice(client, payload)
			operation = "create"

		frappe.db.set_value("Pennylane Customer Invoice", doc_name, {
			"pennylane_id": resp.get("id"),
			"invoice_number": resp.get("invoice_number"),
			"status": resp.get("status", "draft"),
			"amount": resp.get("amount"),
			"currency_amount": resp.get("currency_amount"),
			"sync_status": "Synced",
			"last_synced_at": frappe.utils.now_datetime(),
		})
		write_log(
			direction="push", resource_type="customer_invoice", operation=operation,
			status="Success", frappe_doctype="Pennylane Customer Invoice",
			frappe_docname=doc_name, pennylane_id=resp.get("id"),
			request_payload=payload, response_payload=resp,
		)

	except Exception as exc:
		frappe.db.set_value("Pennylane Customer Invoice", doc_name, "sync_status", "Failed")
		write_log(
			direction="push", resource_type="customer_invoice",
			operation="create" if not existing_id else "update",
			status="Failed", frappe_doctype="Pennylane Customer Invoice",
			frappe_docname=doc_name, request_payload=payload, error_message=str(exc),
			http_status_code=getattr(exc, "status_code", None),
		)
		frappe.log_error(str(exc), f"Pennylane push_invoice: {doc_name}")
		raise


# ------------------------------------------------------------------
# Pull
# ------------------------------------------------------------------


def pull_invoices():
	if not is_integration_enabled():
		return

	settings = frappe.get_cached_doc("Pennylane Settings")
	if not settings.sync_invoices:
		return

	client = PennylaneClient.from_settings()
	cursor = settings.invoice_changelog_cursor or None

	resp = get_changelog(client, cursor=cursor)
	items = resp.get("items", [])

	for change in items:
		try:
			pl_id = change["id"]
			op = change["operation"]
			if op == "delete":
				_handle_delete(pl_id)
				continue
			_upsert(get_invoice(client, pl_id), client)
		except Exception as exc:
			write_log(
				direction="pull", resource_type="customer_invoice",
				operation=change.get("operation", "unknown"), status="Failed",
				pennylane_id=change.get("id"), error_message=str(exc),
			)
			frappe.log_error(str(exc), f"Pennylane pull_invoices id={change.get('id')}")

	next_cursor = (
		resp.get("next_cursor")
		if resp.get("has_more")
		else (items[-1].get("id") if items else cursor)
	)
	frappe.db.set_value(
		"Pennylane Settings", "Pennylane Settings", "invoice_changelog_cursor", next_cursor
	)


def full_sync_invoices():
	"""Pull all invoices from the list endpoint (force full sync)."""
	if not is_integration_enabled():
		return
	client = PennylaneClient.from_settings()
	for pl_invoice in list_invoices(client):
		try:
			_upsert(pl_invoice, client)
		except Exception as exc:
			frappe.log_error(str(exc), f"Pennylane full_sync_invoices id={pl_invoice.get('id')}")
	frappe.db.set_value(
		"Pennylane Settings", "Pennylane Settings", "invoice_changelog_cursor", None
	)


def _upsert(pl_data: dict, client: PennylaneClient):
	pl_id = pl_data.get("id")

	pl_customer = pl_data.get("customer") or {}
	if pl_customer.get("id"):
		_ensure_customer_from_pl(pl_customer["id"], client)

	fields = from_pennylane(pl_data)
	is_finalized = not fields.pop("_draft", True)
	is_cancelled = fields.get("status") == "cancelled"

	doc_name = frappe.db.get_value("Pennylane Customer Invoice", {"pennylane_id": pl_id}, "name")
	sync_meta = {"sync_status": "Synced", "last_synced_at": frappe.utils.now_datetime()}

	if doc_name:
		doc = frappe.get_doc("Pennylane Customer Invoice", doc_name)
		doc.flags[_SYNC_FLAG] = "pennylane"

		if doc.docstatus == 0:
			# Still a draft — full update
			doc.update({k: v for k, v in fields.items() if k != "invoice_lines"})
			doc.set("invoice_lines", fields.get("invoice_lines", []))
			doc.update(sync_meta)
			doc.save(ignore_permissions=True)

			if is_cancelled:
				doc.cancel()
			elif is_finalized:
				doc.submit()
		else:
			# Already submitted/cancelled — only update read-only metadata via set_value
			update = {
				"status": fields.get("status"),
				"amount": fields.get("amount"),
				"currency_amount": fields.get("currency_amount"),
				**sync_meta,
			}
			frappe.db.set_value("Pennylane Customer Invoice", doc_name, update)

		_try_attach_pdf(doc, pl_data)
		write_log(
			direction="pull", resource_type="customer_invoice", operation="update",
			status="Success", frappe_doctype="Pennylane Customer Invoice",
			frappe_docname=doc_name, pennylane_id=pl_id,
		)
	else:
		doc = frappe.new_doc("Pennylane Customer Invoice")
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update({k: v for k, v in fields.items() if k != "invoice_lines"})
		doc.set("invoice_lines", fields.get("invoice_lines", []))
		doc.update(sync_meta)
		doc.insert(ignore_permissions=True)

		if is_cancelled:
			doc.cancel()
		elif is_finalized:
			doc.submit()

		_try_attach_pdf(doc, pl_data)
		write_log(
			direction="pull", resource_type="customer_invoice", operation="create",
			status="Success", frappe_doctype="Pennylane Customer Invoice",
			frappe_docname=doc.name, pennylane_id=pl_id,
		)


def _handle_delete(pl_id: int):
	doc_name = frappe.db.get_value("Pennylane Customer Invoice", {"pennylane_id": pl_id}, "name")
	if doc_name:
		frappe.db.set_value("Pennylane Customer Invoice", doc_name, "sync_status", "Failed")
	write_log(
		direction="pull", resource_type="customer_invoice", operation="delete",
		status="Success", pennylane_id=pl_id,
	)


# ------------------------------------------------------------------
# Dependency helpers
# ------------------------------------------------------------------


def _ensure_customer(frappe_customer_name: str):
	pl_id = frappe.db.get_value("Pennylane Customer", frappe_customer_name, "pennylane_id")
	if not pl_id:
		from pennylane.sync.customer import push_customer
		push_customer(frappe_customer_name)


def _ensure_customer_from_pl(pl_customer_id: int, client: PennylaneClient):
	if not frappe.db.exists("Pennylane Customer", {"pennylane_id": pl_customer_id}):
		from pennylane.client.customers import get_customer
		from pennylane.sync.customer import _upsert as upsert_customer
		upsert_customer(get_customer(client, pl_customer_id), client)


def _try_attach_pdf(doc, pl_data: dict) -> None:
	"""Attempt to attach the PDF from Pennylane; swallow errors to not break sync."""
	public_file_url = pl_data.get("public_file_url")
	filename = pl_data.get("filename")
	if not public_file_url or not filename:
		return
	try:
		attach_pdf(doc, public_file_url, filename)
	except Exception as exc:
		frappe.log_error(str(exc), f"Pennylane attach_pdf invoice: {doc.name}")


def _sync_single_from_webhook(pl_id: int) -> None:
	"""Sync a single invoice triggered by a webhook event."""
	if not is_integration_enabled():
		return
	client = PennylaneClient.from_settings()
	try:
		pl_data = get_invoice(client, pl_id)
		_upsert(pl_data, client)
	except Exception as exc:
		write_log(
			direction="pull", resource_type="customer_invoice",
			operation="webhook", status="Failed",
			pennylane_id=pl_id, error_message=str(exc),
		)
		frappe.log_error(str(exc), f"Pennylane webhook invoice id={pl_id}")
		raise
