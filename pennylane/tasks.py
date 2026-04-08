"""
Scheduled background tasks wired up in hooks.py.
"""

import frappe


def hourly():
	"""Pull customer changes from Pennylane changelog — runs every hour."""
	from pennylane.sync.customer import pull_customers

	try:
		pull_customers()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Pennylane hourly task: pull_customers")


def process_sync_queue():
	"""
	Process pending items in Pennylane Sync Queue (retry failed jobs).
	Runs every minute via the 'all' scheduler bucket.
	"""
	import frappe.utils

	pending = frappe.get_all(
		"Pennylane Sync Queue",
		filters={
			"status": ["in", ["Pending", "Failed"]],
			"retry_count": ["<", 5],
			"next_retry_at": ["<=", frappe.utils.now_datetime()],
		},
		fields=["name", "resource_type", "operation", "frappe_doctype", "frappe_docname", "pennylane_id", "retry_count"],
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

	if item.resource_type == "customer":
		push_customer(item.frappe_docname)
