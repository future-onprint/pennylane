"""
Whitelisted API endpoints for triggering manual syncs from the Frappe desk.
"""

import frappe


@frappe.whitelist()
def push_customer(customer_name: str):
	"""Manually push a customer to Pennylane."""
	frappe.has_permission("Customer", doc=customer_name, throw=True)
	frappe.enqueue(
		"pennylane.sync.customer.push_customer",
		queue="default",
		customer_name=customer_name,
	)
	return {"message": f"Customer '{customer_name}' queued for sync."}


@frappe.whitelist()
def push_invoice(invoice_name: str):
	"""Manually push a Sales Invoice to Pennylane."""
	frappe.has_permission("Sales Invoice", doc=invoice_name, throw=True)
	frappe.enqueue(
		"pennylane.sync.invoice.push_invoice",
		queue="default",
		invoice_name=invoice_name,
	)
	return {"message": f"Invoice '{invoice_name}' queued for sync."}


@frappe.whitelist()
def push_quote(quotation_name: str):
	"""Manually push a Quotation to Pennylane."""
	frappe.has_permission("Quotation", doc=quotation_name, throw=True)
	frappe.enqueue(
		"pennylane.sync.quote.push_quote",
		queue="default",
		quotation_name=quotation_name,
	)
	return {"message": f"Quotation '{quotation_name}' queued for sync."}


@frappe.whitelist()
def pull_customers():
	"""Manually trigger customer changelog pull."""
	frappe.only_for("System Manager")
	frappe.enqueue(
		"pennylane.sync.customer.pull_customers",
		queue="default",
	)
	return {"message": "Customer pull job queued."}
