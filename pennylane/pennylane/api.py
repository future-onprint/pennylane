"""Public whitelisted API endpoints for Pennylane."""

import frappe

from pennylane.sync.utils import is_integration_enabled

_DISPATCH = {
	"Pennylane Product": "pennylane.sync.product.push_product",
	"Pennylane Customer": "pennylane.sync.customer.push_customer",
	"Pennylane Customer Invoice": "pennylane.sync.invoice.push_invoice",
	"Pennylane Customer Quote": "pennylane.sync.quote.push_quote",
}


@frappe.whitelist()
def sync_now(doctype: str, docname: str):
	"""Push a single document to Pennylane immediately (synchronous)."""
	if not is_integration_enabled():
		frappe.throw(frappe._("Pennylane integration is not enabled."))

	method = _DISPATCH.get(doctype)
	if not method:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	frappe.get_attr(method)(docname)
	frappe.db.commit()
