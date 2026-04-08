"""
Whitelisted API endpoints for triggering manual syncs from the Frappe desk.
"""

import frappe


@frappe.whitelist()
def push_customer(customer_name: str):
	"""Manually push a Pennylane Customer to Pennylane."""
	frappe.has_permission("Pennylane Customer", doc=customer_name, throw=True)
	frappe.enqueue(
		"pennylane.sync.customer.push_customer",
		queue="default",
		doc_name=customer_name,
	)
	return {"message": f"Customer '{customer_name}' queued for sync."}


@frappe.whitelist()
def push_invoice(invoice_name: str):
	"""Manually push a Pennylane Customer Invoice to Pennylane."""
	frappe.has_permission("Pennylane Customer Invoice", doc=invoice_name, throw=True)
	frappe.enqueue(
		"pennylane.sync.invoice.push_invoice",
		queue="default",
		doc_name=invoice_name,
	)
	return {"message": f"Invoice '{invoice_name}' queued for sync."}


@frappe.whitelist()
def push_quote(quote_name: str):
	"""Manually push a Pennylane Customer Quote to Pennylane."""
	frappe.has_permission("Pennylane Customer Quote", doc=quote_name, throw=True)
	frappe.enqueue(
		"pennylane.sync.quote.push_quote",
		queue="default",
		doc_name=quote_name,
	)
	return {"message": f"Quote '{quote_name}' queued for sync."}


@frappe.whitelist()
def pull_customers():
	"""Manually trigger customer changelog pull."""
	frappe.only_for("System Manager")
	frappe.enqueue("pennylane.sync.customer.pull_customers", queue="default")
	return {"message": "Customer pull job queued."}


@frappe.whitelist()
def pull_invoices():
	"""Manually trigger invoice changelog pull."""
	frappe.only_for("System Manager")
	frappe.enqueue("pennylane.sync.invoice.pull_invoices", queue="default")
	return {"message": "Invoice pull job queued."}


@frappe.whitelist()
def pull_quotes():
	"""Manually trigger quote changelog pull."""
	frappe.only_for("System Manager")
	frappe.enqueue("pennylane.sync.quote.pull_quotes", queue="default")
	return {"message": "Quote pull job queued."}
