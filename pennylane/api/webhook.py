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
	# Always verify HMAC first — do not leak whether webhooks are enabled or not
	raw_body: bytes = frappe.request.data
	signature = frappe.get_request_header("X-Pennylane-Signature") or ""

	secret = frappe.db.get_single_value("Pennylane Settings", "webhook_secret")
	if not secret:
		frappe.response.http_status_code = 401
		return {"status": "unauthorized"}

	secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
	expected = hmac.new(secret_bytes, raw_body, hashlib.sha256).hexdigest()

	if not hmac.compare_digest(expected, signature):
		frappe.response.http_status_code = 401
		return {"status": "unauthorized"}

	# Signature valid — now check if webhooks are enabled
	enable_webhooks = frappe.db.get_single_value("Pennylane Settings", "enable_webhooks")
	if not enable_webhooks:
		return {"status": "ok"}

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

	# Deduplication: skip events we've already processed within the last 60 seconds
	# to handle Pennylane's at-least-once delivery guarantee
	dedup_key = f"pennylane_webhook:{event_type}:{resource_id}"
	if frappe.cache().get(dedup_key):
		return {"status": "ok"}
	frappe.cache().set(dedup_key, "1", ex=60)

	# Dispatch to appropriate sync job
	_dispatch(event_type, resource_id)

	return {"status": "ok"}


def _dispatch(event_type: str, resource_id):
	"""Enqueue the correct pull job based on event_type."""
	if event_type == "customer_invoice.created":
		frappe.enqueue(
			"pennylane.sync.invoice._sync_single_from_webhook",
			queue="default",
			enqueue_after_commit=True,
			pl_id=resource_id,
		)
	elif event_type == "quote.created":
		frappe.enqueue(
			"pennylane.sync.quote._sync_single_from_webhook",
			queue="default",
			enqueue_after_commit=True,
			pl_id=resource_id,
		)
	else:
		frappe.log_error(
			f"Unhandled Pennylane webhook event: {event_type} (id={resource_id})",
			"Pennylane Webhook",
		)
