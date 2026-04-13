"""Scheduled background tasks wired up in hooks.py."""

import json
import random

import frappe

from pennylane.sync.utils import is_integration_enabled


_PULL_JOBS = [
	"pennylane.sync.customer.pull_customers",
	"pennylane.sync.invoice.pull_invoices",
	"pennylane.sync.quote.pull_quotes",
	"pennylane.sync.product.pull_products",
]

_PULL_TIMEOUT = 1500  # seconds — 25 min, well above the default 300s


def hourly():
	"""Enqueue each pull job individually so each gets its own 1500 s timeout."""
	for method in _PULL_JOBS:
		frappe.enqueue(
			method,
			queue="long",
			timeout=_PULL_TIMEOUT,
			now=frappe.flags.in_test,
		)


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
			jitter = random.uniform(0, min(60, 2 ** retry_count))
			next_retry = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=2 ** retry_count + jitter)
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
	"""Delete Sync Logs older than the configured retention period and clean up abandoned queue items."""
	retention = frappe.db.get_single_value("Pennylane Settings", "log_retention_days") or 0

	if retention:
		cutoff = frappe.utils.add_days(frappe.utils.nowdate(), -int(retention))
		# Preserve Failed logs regardless of age — needed for audit trail
		frappe.db.delete("Pennylane Sync Log", {
			"creation": ["<", cutoff],
			"status": ["!=", "Failed"],
		})

	# Clean up abandoned queue items older than retention days (default 30)
	abandoned_cutoff = frappe.utils.add_days(frappe.utils.nowdate(), -int(retention or 30))
	frappe.db.delete("Pennylane Sync Queue", {
		"status": "Abandoned",
		"creation": ["<", abandoned_cutoff],
	})

	frappe.db.commit()


def _run(method: str, label: str):
	try:
		frappe.get_attr(method)()
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"Pennylane hourly: {label}")
