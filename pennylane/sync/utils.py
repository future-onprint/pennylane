"""Shared helpers for sync handlers."""

import json

import frappe
import frappe.utils


_OPERATION_MAP = {"insert": "create"}


def write_log(
	direction: str,
	resource_type: str,
	operation: str,
	status: str,
	frappe_doctype: str = None,
	frappe_docname: str = None,
	pennylane_id=None,
	request_payload: dict = None,
	response_payload: dict = None,
	error_message: str = None,
	http_status_code: int = None,
):
	log = frappe.new_doc("Pennylane Sync Log")
	log.direction = direction
	log.resource_type = resource_type
	log.operation = _OPERATION_MAP.get(operation, operation)
	log.status = status
	log.frappe_doctype = frappe_doctype
	log.frappe_docname = frappe_docname
	log.pennylane_id = str(pennylane_id) if pennylane_id else None
	log.request_payload = json.dumps(request_payload, default=str) if request_payload else None
	log.response_payload = json.dumps(response_payload, default=str) if response_payload else None
	log.error_message = error_message
	log.http_status_code = http_status_code
	log.insert(ignore_permissions=True)

	if status == "Failed":
		_notify_on_failure(
			direction=direction,
			resource_type=resource_type,
			operation=operation,
			frappe_doctype=frappe_doctype,
			frappe_docname=frappe_docname,
			pennylane_id=pennylane_id,
			error_message=error_message,
		)


def _notify_on_failure(
	direction: str,
	resource_type: str,
	operation: str,
	frappe_doctype: str = None,
	frappe_docname: str = None,
	pennylane_id=None,
	error_message: str = None,
) -> None:
	"""Publish a realtime event and create a Notification Log for System Managers."""
	try:
		notify = frappe.db.get_single_value("Pennylane Settings", "notify_on_failure")
		if not notify:
			return

		subject = (
			f"Pennylane sync failed: {operation} {resource_type}"
			+ (f" ({frappe_doctype} {frappe_docname})" if frappe_docname else "")
		)
		message = error_message or "No details available."

		event_data = {
			"direction": direction,
			"resource_type": resource_type,
			"operation": operation,
			"frappe_doctype": frappe_doctype,
			"frappe_docname": frappe_docname,
			"pennylane_id": str(pennylane_id) if pennylane_id else None,
			"error_message": message,
		}

		# Realtime notification (broadcasts to all logged-in users)
		frappe.publish_realtime("pennylane_sync_failed", event_data)

		# Create a Frappe Notification Log for each System Manager user
		system_managers = frappe.get_all(
			"Has Role",
			filters={"role": "System Manager", "parenttype": "User"},
			pluck="parent",
		)
		# Filter to active, non-guest users
		if system_managers:
			active_managers = frappe.get_all(
				"User",
				filters={
					"name": ["in", system_managers],
					"enabled": 1,
					"user_type": "System User",
				},
				pluck="name",
			)
			for user in active_managers:
				notif = frappe.new_doc("Notification Log")
				notif.subject = subject
				notif.for_user = user
				notif.type = "Alert"
				notif.document_type = frappe_doctype or "Pennylane Sync Log"
				notif.document_name = frappe_docname or ""
				notif.insert(ignore_permissions=True)
	except Exception as exc:
		# Notification failure must never break the sync flow
		frappe.log_error(str(exc), "Pennylane _notify_on_failure")


def notify_full_sync_complete(resource_type: str, ok: int, errors: int) -> None:
	"""Push a Frappe Notification Log to all System Managers when a full sync finishes."""
	try:
		_LABELS = {
			"customer": "Customers",
			"customer_invoice": "Customer Invoices",
			"customer_quote": "Quotes",
			"product": "Products",
		}
		label = _LABELS.get(resource_type, resource_type)
		has_errors = errors > 0

		subject = f"Pennylane Full Sync — {label}: {ok} imported" + (
			f", {errors} error(s)" if has_errors else ""
		)

		system_managers = frappe.get_all(
			"Has Role",
			filters={"role": ["in", ["System Manager", "Pennylane Manager"]], "parenttype": "User"},
			pluck="parent",
		)
		if not system_managers:
			return

		active_users = frappe.get_all(
			"User",
			filters={"name": ["in", system_managers], "enabled": 1, "user_type": "System User"},
			pluck="name",
		)
		for user in set(active_users):
			notif = frappe.new_doc("Notification Log")
			notif.subject = subject
			notif.for_user = user
			notif.type = "Alert" if has_errors else "Mention"
			notif.document_type = "Pennylane Sync Log"
			notif.document_name = ""
			notif.insert(ignore_permissions=True)

		frappe.db.commit()
	except Exception as exc:
		frappe.log_error(str(exc), "Pennylane notify_full_sync_complete")


def enqueue_sync(
	resource_type: str,
	frappe_doctype: str,
	frappe_docname: str,
	operation: str = "update",
	**kwargs,
):
	"""Insert a Pennylane Sync Queue record for deferred push with retry.

	If a Pending or Failed entry already exists for the same document it is
	reset to Pending (de-duplication) so the latest state is always pushed.
	Extra keyword arguments (e.g. finalized=True for invoices) are stored in
	the payload JSON field and forwarded to the push function at dispatch time.
	"""
	payload = json.dumps(kwargs) if kwargs else None

	existing = frappe.db.get_value(
		"Pennylane Sync Queue",
		{"resource_type": resource_type, "frappe_docname": frappe_docname, "status": ["in", ["Pending", "Failed"]]},
		"name",
	)
	if existing:
		frappe.db.set_value(
			"Pennylane Sync Queue",
			existing,
			{"status": "Pending", "retry_count": 0, "next_retry_at": frappe.utils.now_datetime(), "payload": payload},
		)
		return

	doc = frappe.new_doc("Pennylane Sync Queue")
	doc.resource_type = resource_type
	doc.frappe_doctype = frappe_doctype
	doc.frappe_docname = frappe_docname
	doc.operation = operation
	doc.status = "Pending"
	doc.next_retry_at = frappe.utils.now_datetime()
	doc.payload = payload
	doc.insert(ignore_permissions=True)


def set_creation(doctype: str, docname: str, creation: str) -> None:
	"""Set the `creation` timestamp on an existing record using raw SQL.

	Frappe v15 blocks `frappe.db.set_value` on the `creation` system field,
	so a direct UPDATE is the only reliable way to backfill it from Pennylane.
	"""
	frappe.db.sql(
		f"UPDATE `tab{doctype}` SET `creation` = %s WHERE `name` = %s",
		(creation, docname),
	)



def is_integration_enabled() -> bool:
	settings = frappe.get_cached_doc("Pennylane Settings")
	return bool(settings.is_enabled and settings.get_password("api_token"))
