"""Shared helpers for sync handlers."""

import json

import frappe
import frappe.utils


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
	log.operation = operation
	log.status = status
	log.frappe_doctype = frappe_doctype
	log.frappe_docname = frappe_docname
	log.pennylane_id = str(pennylane_id) if pennylane_id else None
	log.request_payload = json.dumps(request_payload, default=str) if request_payload else None
	log.response_payload = json.dumps(response_payload, default=str) if response_payload else None
	log.error_message = error_message
	log.http_status_code = http_status_code
	log.insert(ignore_permissions=True)


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
