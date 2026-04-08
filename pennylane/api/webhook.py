"""
Pennylane webhook endpoint.

URL: /api/method/pennylane.api.webhook.handle_webhook
Allowed for guest users (whitelisted).
"""

import hashlib
import hmac
import json

import frappe


@frappe.whitelist(allow_guest=True)
def handle_webhook():
	"""Receive and dispatch Pennylane webhook events."""
	# Read raw body and signature
	raw_body: bytes = frappe.request.data
	signature = frappe.get_request_header("X-Pennylane-Signature") or ""

	# Verify HMAC-SHA256 signature
	secret = frappe.db.get_single_value("Pennylane Settings", "webhook_secret")
	if not secret:
		frappe.throw("Webhook secret not configured", frappe.AuthenticationError)

	secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
	expected = hmac.new(secret_bytes, raw_body, hashlib.sha256).hexdigest()

	if not hmac.compare_digest(expected, signature):
		frappe.response.http_status_code = 401
		return {"status": "unauthorized", "message": "Invalid signature"}

	# Parse body
	try:
		payload = json.loads(raw_body)
	except Exception:
		frappe.response.http_status_code = 400
		return {"status": "error", "message": "Invalid JSON body"}

	event_type = payload.get("event_type")
	resource_id = payload.get("id")

	if not event_type:
		frappe.response.http_status_code = 400
		return {"status": "error", "message": "Missing event_type"}

	# Dispatch to appropriate sync job
	_dispatch(event_type, resource_id)

	return {"status": "ok"}


def _dispatch(event_type: str, resource_id):
	"""Enqueue the correct sync job based on event_type."""
	from pennylane.sync.utils import enqueue_sync

	if event_type == "customer_invoice.created":
		enqueue_sync(
			"pennylane.sync.invoice._sync_single_from_webhook",
			pl_id=resource_id,
		)
	elif event_type == "quote.created":
		enqueue_sync(
			"pennylane.sync.quote._sync_single_from_webhook",
			pl_id=resource_id,
		)
	else:
		frappe.log_error(
			f"Unhandled Pennylane webhook event: {event_type} (id={resource_id})",
			"Pennylane Webhook",
		)
