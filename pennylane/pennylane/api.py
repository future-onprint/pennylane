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
