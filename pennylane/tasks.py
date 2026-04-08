"""Scheduled background tasks wired up in hooks.py."""

import frappe


def hourly():
	"""Pull changes from all Pennylane changelogs."""
	_run("pennylane.sync.customer.pull_customers", "pull_customers")
	_run("pennylane.sync.invoice.pull_invoices", "pull_invoices")
	_run("pennylane.sync.quote.pull_quotes", "pull_quotes")
	_run("pennylane.sync.product.pull_products", "pull_products")


def process_sync_queue():
	"""Retry failed push jobs — runs every minute via 'all' scheduler bucket."""
	import frappe.utils

	pending = frappe.get_all(
		"Pennylane Sync Queue",
		filters={
			"status": ["in", ["Pending", "Failed"]],
			"retry_count": ["<", 5],
			"next_retry_at": ["<=", frappe.utils.now_datetime()],
		},
		fields=["name", "resource_type", "frappe_doctype", "frappe_docname", "retry_count"],
		order_by="creation asc",
		limit=50,
	)

	for item in pending:
		frappe.db.set_value("Pennylane Sync Queue", item.name, "status", "Processing")
		try:
			_dispatch_queue_item(item)
			frappe.db.set_value("Pennylane Sync Queue", item.name, "status", "Success")
		except Exception as exc:
			retry_count = item.retry_count + 1
			next_retry = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=2**retry_count)
			frappe.db.set_value(
				"Pennylane Sync Queue",
				item.name,
				{
					"status": "Abandoned" if retry_count >= 5 else "Failed",
					"retry_count": retry_count,
					"next_retry_at": next_retry,
				},
			)
			frappe.log_error(str(exc), f"Pennylane sync queue: {item.name}")


def _dispatch_queue_item(item):
	from pennylane.sync.customer import push_customer
	from pennylane.sync.invoice import push_invoice
	from pennylane.sync.product import push_product
	from pennylane.sync.quote import push_quote

	dispatch = {
		"customer": push_customer,
		"customer_invoice": push_invoice,
		"customer_quote": push_quote,
		"product": push_product,
	}
	fn = dispatch.get(item.resource_type)
	if fn:
		fn(item.frappe_docname)


def _run(method: str, label: str):
	try:
		frappe.get_attr(method)()
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Pennylane hourly: {label}")
