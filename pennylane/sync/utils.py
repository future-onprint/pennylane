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


def enqueue_sync(method: str, **kwargs):
	"""Enqueue a background sync job after the current DB transaction commits."""
	frappe.enqueue(
		method,
		queue="default",
		enqueue_after_commit=True,
		**kwargs,
	)


def is_integration_enabled() -> bool:
	settings = frappe.get_cached_doc("Pennylane Settings")
	return bool(settings.is_enabled and settings.get_password("api_token"))
