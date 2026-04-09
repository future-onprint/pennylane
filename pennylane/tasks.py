"""Scheduled background tasks wired up in hooks.py."""

import json

import frappe

from pennylane.sync.utils import is_integration_enabled


def hourly():
	"""Pull changes from all Pennylane changelogs."""
	_run("pennylane.sync.customer.pull_customers", "pull_customers")
	_run("pennylane.sync.invoice.pull_invoices", "pull_invoices")
	_run("pennylane.sync.quote.pull_quotes", "pull_quotes")
	_run("pennylane.sync.product.pull_products", "pull_products")


def process_sync_queue():
	"""Retry failed push jobs — runs every minute via 'all' scheduler bucket."""
	if not is_integration_enabled():
		return

	pending = frappe.get_all(
		"Pennylane Sync Queue",
		filters={
			"status": ["in", ["Pending", "Failed"]],
			"retry_count": ["<", 5],
			"next_retry_at": ["<=", frappe.utils.now_datetime()],
		},
		fields=["name", "resource_type", "frappe_doctype", "frappe_docname", "retry_count", "payload"],
		order_by="creation asc",
		limit=50,
	)

	for item in pending:
		frappe.db.set_value("Pennylane Sync Queue", item.name, "status", "Processing")
		try:
			_dispatch_queue_item(item)
			# Success — remove from queue (Sync Log already records it)
			frappe.delete_doc("Pennylane Sync Queue", item.name, ignore_permissions=True, force=True)
		except Exception as exc:
			retry_count = item.retry_count + 1
			next_retry = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=2 ** retry_count)
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
	if not fn:
		return

	kwargs = json.loads(item.payload) if item.payload else {}
	fn(item.frappe_docname, **kwargs)


def daily():
	"""Delete Sync Logs older than the configured retention period."""
	retention = frappe.db.get_single_value("Pennylane Settings", "log_retention_days") or 0
	if not retention:
		return

	cutoff = frappe.utils.add_days(frappe.utils.nowdate(), -int(retention))
	frappe.db.delete("Pennylane Sync Log", {"creation": ["<", cutoff]})
	frappe.db.commit()


def _run(method: str, label: str):
	try:
		frappe.get_attr(method)()
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Pennylane hourly: {label}")
