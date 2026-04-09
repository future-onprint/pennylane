"""Pennylane Customer Quote sync — push on save/submit, pull via changelog.

A quote is editable while its status is `pending`. Once Pennylane moves it to
`accepted`, `denied`, `invoiced`, or `expired` the Frappe doc is automatically
submitted (read-only). A quote can be linked to one or many invoices via the
`linked_invoices` relationship on the Pennylane side.
"""

import frappe
import frappe.utils

from pennylane.client.base import PennylaneClient
from pennylane.utils.pdf import attach_pdf
from pennylane.client.quotes import (
	create_quote,
	get_changelog,
	get_quote,
	list_quotes,
	update_quote,
)
from pennylane.mappers.quote import from_pennylane, to_pennylane
from pennylane.sync.utils import enqueue_sync, is_integration_enabled, write_log

_SYNC_FLAG = "pennylane_sync_source"

# Statuses that lock the quote from further edits
_LOCKED_STATUSES = {"accepted", "denied", "invoiced", "expired"}


# ------------------------------------------------------------------
# Doc events
# ------------------------------------------------------------------


def on_quote_save(doc, method=None):
	"""Fired on after_insert / on_update — only for pending (docstatus=0) docs."""
	if getattr(doc.flags, _SYNC_FLAG, None) == "pennylane":
		return
	if not is_integration_enabled():
		return
	if doc.docstatus != 0:
		return
	settings = frappe.get_cached_doc("Pennylane Settings")
	if not settings.sync_quotes:
		return
	enqueue_sync("pennylane.sync.quote.push_quote", doc_name=doc.name)


def on_quote_submit(doc, method=None):
	"""Fired on on_submit — not used for push (quotes have no finalization step).

	Submission happens automatically on pull when Pennylane locks the quote.
	This hook exists to prevent accidental manual submission triggering a push.
	"""
	pass


def on_quote_cancel(doc, method=None):
	"""Fired on on_cancel."""
	if getattr(doc.flags, _SYNC_FLAG, None) == "pennylane":
		return
	frappe.db.set_value("Pennylane Customer Quote", doc.name, "sync_status", "Failed")
	write_log(
		direction="push", resource_type="customer_quote", operation="cancel",
		status="Info", frappe_doctype="Pennylane Customer Quote", frappe_docname=doc.name,
		pennylane_id=doc.pennylane_id,
		error_message="Quote cancelled in Frappe. Manual action may be required in Pennylane.",
	)


# ------------------------------------------------------------------
# Push
# ------------------------------------------------------------------


def push_quote(doc_name: str):
	doc = frappe.get_doc("Pennylane Customer Quote", doc_name)

	_ensure_customer(doc.customer)

	client = PennylaneClient.from_settings()
	payload = to_pennylane(doc_name)
	existing_id = doc.pennylane_id

	try:
		if existing_id:
			resp = update_quote(client, existing_id, payload)
			operation = "update"
		else:
			resp = create_quote(client, payload)
			operation = "create"

		frappe.db.set_value("Pennylane Customer Quote", doc_name, {
			"pennylane_id": resp.get("id"),
			"quote_number": resp.get("quote_number"),
			"status": resp.get("status", "pending"),
			"amount": resp.get("amount"),
			"currency_amount": resp.get("currency_amount"),
			"sync_status": "Synced",
			"last_synced_at": frappe.utils.now_datetime(),
		})
		write_log(
			direction="push", resource_type="customer_quote", operation=operation,
			status="Success", frappe_doctype="Pennylane Customer Quote",
			frappe_docname=doc_name, pennylane_id=resp.get("id"),
			request_payload=payload, response_payload=resp,
		)

	except Exception as exc:
		frappe.db.set_value("Pennylane Customer Quote", doc_name, "sync_status", "Failed")
		write_log(
			direction="push", resource_type="customer_quote",
			operation="create" if not existing_id else "update",
			status="Failed", frappe_doctype="Pennylane Customer Quote",
			frappe_docname=doc_name, request_payload=payload, error_message=str(exc),
			http_status_code=getattr(exc, "status_code", None),
		)
		frappe.log_error(str(exc), f"Pennylane push_quote: {doc_name}")
		raise


# ------------------------------------------------------------------
# Pull
# ------------------------------------------------------------------


def pull_quotes():
	if not is_integration_enabled():
		return

	settings = frappe.get_cached_doc("Pennylane Settings")
	if not settings.sync_quotes:
		return

	client = PennylaneClient.from_settings()
	cursor = settings.quote_changelog_cursor or None

	resp = get_changelog(client, cursor=cursor)
	items = resp.get("items", [])

	for change in items:
		try:
			pl_id = change["id"]
			op = change["operation"]
			if op == "delete":
				_handle_delete(pl_id)
				continue
			_upsert(get_quote(client, pl_id), client)
		except Exception as exc:
			write_log(
				direction="pull", resource_type="customer_quote",
				operation=change.get("operation", "unknown"), status="Failed",
				pennylane_id=change.get("id"), error_message=str(exc),
			)
			frappe.log_error(str(exc), f"Pennylane pull_quotes id={change.get('id')}")

	next_cursor = (
		resp.get("next_cursor")
		if resp.get("has_more")
		else (items[-1].get("id") if items else cursor)
	)
	frappe.db.set_value(
		"Pennylane Settings", "Pennylane Settings", "quote_changelog_cursor", next_cursor
	)


def full_sync_quotes():
	"""Pull all quotes from the list endpoint (force full sync)."""
	if not is_integration_enabled():
		return
	client = PennylaneClient.from_settings()
	for pl_quote in list_quotes(client):
		try:
			_upsert(pl_quote, client)
		except Exception as exc:
			frappe.log_error(str(exc), f"Pennylane full_sync_quotes id={pl_quote.get('id')}")
	frappe.db.set_value(
		"Pennylane Settings", "Pennylane Settings", "quote_changelog_cursor", None
	)


def _upsert(pl_data: dict, client: PennylaneClient):
	pl_id = pl_data.get("id")

	pl_customer = pl_data.get("customer") or {}
	if pl_customer.get("id"):
		_ensure_customer_from_pl(pl_customer["id"], client)

	fields = from_pennylane(pl_data)
	is_locked = fields.pop("_locked", False)

	doc_name = frappe.db.get_value("Pennylane Customer Quote", {"pennylane_id": pl_id}, "name")
	sync_meta = {"sync_status": "Synced", "last_synced_at": frappe.utils.now_datetime()}

	if doc_name:
		doc = frappe.get_doc("Pennylane Customer Quote", doc_name)
		doc.flags[_SYNC_FLAG] = "pennylane"

		if doc.docstatus == 0:
			doc.update({k: v for k, v in fields.items() if k != "invoice_lines"})
			doc.set("invoice_lines", fields.get("invoice_lines", []))
			doc.update(sync_meta)
			doc.save(ignore_permissions=True)

			if is_locked:
				doc.submit()
		else:
			# Already submitted — only update read-only metadata
			update = {
				"status": fields.get("status"),
				"amount": fields.get("amount"),
				"currency_amount": fields.get("currency_amount"),
				**sync_meta,
			}
			frappe.db.set_value("Pennylane Customer Quote", doc_name, update)

		_try_attach_pdf(doc, pl_data)
		write_log(
			direction="pull", resource_type="customer_quote", operation="update",
			status="Success", frappe_doctype="Pennylane Customer Quote",
			frappe_docname=doc_name, pennylane_id=pl_id,
		)
	else:
		doc = frappe.new_doc("Pennylane Customer Quote")
		doc.flags[_SYNC_FLAG] = "pennylane"
		doc.update({k: v for k, v in fields.items() if k != "invoice_lines"})
		doc.set("invoice_lines", fields.get("invoice_lines", []))
		doc.update(sync_meta)
		doc.insert(ignore_permissions=True)

		if is_locked:
			doc.submit()

		_try_attach_pdf(doc, pl_data)
		write_log(
			direction="pull", resource_type="customer_quote", operation="create",
			status="Success", frappe_doctype="Pennylane Customer Quote",
			frappe_docname=doc.name, pennylane_id=pl_id,
		)


def _handle_delete(pl_id: int):
	doc_name = frappe.db.get_value("Pennylane Customer Quote", {"pennylane_id": pl_id}, "name")
	if doc_name:
		frappe.db.set_value("Pennylane Customer Quote", doc_name, "sync_status", "Deleted")
	write_log(
		direction="pull", resource_type="customer_quote", operation="delete",
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
		from pennylane.client.exceptions import PennylaneNotFoundError
		from pennylane.sync.customer import _upsert as upsert_customer
		try:
			upsert_customer(get_customer(client, pl_customer_id), client)
		except PennylaneNotFoundError:
			frappe.log_error(
				f"Customer {pl_customer_id} not found in Pennylane — skipping auto-create.",
				"Pennylane _ensure_customer_from_pl",
			)


def _try_attach_pdf(doc, pl_data: dict) -> None:
	"""Attempt to attach the PDF from Pennylane; swallow errors to not break sync."""
	public_file_url = pl_data.get("public_file_url")
	filename = pl_data.get("filename")
	if not public_file_url or not filename:
		return
	try:
		attach_pdf(doc, public_file_url, filename)
	except Exception as exc:
		frappe.log_error(str(exc), f"Pennylane attach_pdf quote: {doc.name}")


def _sync_single_from_webhook(pl_id: int) -> None:
	"""Sync a single quote triggered by a webhook event."""
	if not is_integration_enabled():
		return
	client = PennylaneClient.from_settings()
	try:
		pl_data = get_quote(client, pl_id)
		_upsert(pl_data, client)
	except Exception as exc:
		write_log(
			direction="pull", resource_type="customer_quote",
			operation="webhook", status="Failed",
			pennylane_id=pl_id, error_message=str(exc),
		)
		frappe.log_error(str(exc), f"Pennylane webhook quote id={pl_id}")
		raise
