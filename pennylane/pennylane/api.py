"""Public whitelisted API endpoints for Pennylane."""

import frappe

from pennylane.client.exceptions import PennylaneNotFoundError
from pennylane.sync.utils import is_integration_enabled

_DISPATCH = {
	"Pennylane Product": "pennylane.sync.product.push_product",
	"Pennylane Customer": "pennylane.sync.customer.push_customer",
	"Pennylane Customer Invoice": "pennylane.sync.invoice.push_invoice",
	"Pennylane Customer Quote": "pennylane.sync.quote.push_quote",
}

_PULL_DISPATCH = {
	"Pennylane Product": "pennylane.sync.product.pull_products",
	"Pennylane Customer": "pennylane.sync.customer.pull_customers",
	"Pennylane Customer Invoice": "pennylane.sync.invoice.pull_invoices",
	"Pennylane Customer Quote": "pennylane.sync.quote.pull_quotes",
}

_DELETABLE_DOCTYPES = {
	"Pennylane Product",
	"Pennylane Customer",
	"Pennylane Customer Invoice",
	"Pennylane Customer Quote",
}


@frappe.whitelist()
def sync_now(doctype: str, docname: str):
	"""Push a single document to Pennylane immediately (synchronous)."""
	if not is_integration_enabled():
		frappe.throw(frappe._("Pennylane integration is not enabled."))

	method = _DISPATCH.get(doctype)
	if not method:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	try:
		frappe.get_attr(method)(docname)
	except PennylaneNotFoundError:
		frappe.db.set_value(doctype, docname, "sync_status", "Deleted")
		frappe.db.commit()
		return {"status": "deleted"}

	frappe.db.commit()
	return {"status": "synced"}


@frappe.whitelist()
def sync_all(doctype: str):
	"""Pull the latest changes from Pennylane for a resource type (enqueued)."""
	if not is_integration_enabled():
		frappe.throw(frappe._("Pennylane integration is not enabled."))

	method = _PULL_DISPATCH.get(doctype)
	if not method:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	frappe.enqueue(method, queue="default", enqueue_after_commit=True)
	return {"status": "queued"}


@frappe.whitelist()
def delete_doc(doctype: str, docname: str):
	"""Permanently delete a single record marked as Deleted."""
	if doctype not in _DELETABLE_DOCTYPES:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	status = frappe.db.get_value(doctype, docname, "sync_status")
	if status != "Deleted":
		frappe.throw(frappe._("Only records marked as Deleted can be deleted this way."))

	frappe.delete_doc(doctype, docname, ignore_permissions=True, force=True)
	frappe.db.commit()


@frappe.whitelist()
def cleanup_deleted(doctype: str):
	"""Delete all Frappe records marked as Deleted (removed from Pennylane)."""
	if doctype not in _DELETABLE_DOCTYPES:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	names = frappe.get_all(doctype, filters={"sync_status": "Deleted"}, pluck="name")
	count = 0
	for name in names:
		frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
		count += 1

	frappe.db.commit()
	return {"deleted": count}
