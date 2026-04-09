"""Public whitelisted API endpoints for Pennylane."""

import frappe

from pennylane.client.exceptions import PennylaneNotFoundError
from pennylane.sync.utils import is_integration_enabled

_PULL_SINGLE_DISPATCH = {
	"Pennylane Product": "pennylane.sync.product.pull_single",
	"Pennylane Customer": "pennylane.sync.customer.pull_single",
	"Pennylane Customer Invoice": "pennylane.sync.invoice.pull_single",
	"Pennylane Customer Quote": "pennylane.sync.quote.pull_single",
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
	"""Pull a single document from Pennylane immediately (synchronous)."""
	frappe.only_for(["System Manager", "Pennylane Manager"])
	if not is_integration_enabled():
		frappe.throw(frappe._("Pennylane integration is not enabled."))

	method = _PULL_SINGLE_DISPATCH.get(doctype)
	if not method:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	pl_id = frappe.db.get_value(doctype, docname, "pennylane_id")
	if not pl_id:
		frappe.throw(frappe._("This record has no Pennylane ID yet. Save it first to push it to Pennylane."))

	try:
		frappe.get_attr(method)(pl_id)
	except PennylaneNotFoundError:
		frappe.db.set_value(doctype, docname, "sync_status", "Deleted")
		frappe.db.commit()
		return {"status": "deleted"}

	frappe.db.commit()
	return {"status": "synced"}


@frappe.whitelist()
def sync_all(doctype: str):
	"""Pull the latest changes from Pennylane for a resource type (enqueued)."""
	frappe.only_for(["System Manager", "Pennylane Manager"])
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
	frappe.only_for(["System Manager", "Pennylane Manager"])
	if doctype not in _DELETABLE_DOCTYPES:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	status = frappe.db.get_value(doctype, docname, "sync_status")
	if status != "Deleted":
		frappe.throw(frappe._("Only records marked as Deleted can be deleted this way."))

	frappe.delete_doc(doctype, docname, ignore_permissions=True, force=True)
	frappe.db.commit()


@frappe.whitelist()
def cleanup_sync_logs(keep_failed: bool = True, older_than_days: int = 0):
	"""Enqueue a background job to delete Sync Log records.

	- keep_failed=True  → never delete Failed logs (default)
	- older_than_days=0 → delete all matching logs regardless of age
	- older_than_days=N → only delete logs older than N days
	"""
	frappe.only_for("System Manager")
	frappe.enqueue(
		"pennylane.pennylane.api._do_cleanup_sync_logs",
		queue="long",
		keep_failed=keep_failed,
		older_than_days=int(older_than_days),
	)
	return {"queued": True}


def _do_cleanup_sync_logs(keep_failed: bool = True, older_than_days: int = 0):
	"""Background worker: delete Sync Log records matching the given criteria."""
	filters = {}
	if keep_failed:
		filters["status"] = ["!=", "Failed"]
	if older_than_days:
		cutoff = frappe.utils.add_days(frappe.utils.nowdate(), -int(older_than_days))
		filters["creation"] = ["<", cutoff]

	frappe.db.delete("Pennylane Sync Log", filters)
	frappe.db.commit()


@frappe.whitelist()
def cleanup_deleted(doctype: str):
	"""Delete all Frappe records marked as Deleted (removed from Pennylane)."""
	frappe.only_for(["System Manager", "Pennylane Manager"])
	if doctype not in _DELETABLE_DOCTYPES:
		frappe.throw(frappe._("Unsupported DocType: {0}").format(doctype))

	names = frappe.get_all(doctype, filters={"sync_status": "Deleted"}, pluck="name")
	count = 0
	for name in names:
		frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
		count += 1

	frappe.db.commit()
	return {"deleted": count}
