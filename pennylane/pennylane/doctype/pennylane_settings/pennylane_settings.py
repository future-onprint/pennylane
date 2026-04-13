import frappe
import frappe.utils
from frappe.model.document import Document


class PennylaneSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_token: DF.Password | None
		base_url: DF.Data | None
		company_id: DF.Data | None
		connection_status: DF.Literal["", "Connected", "Failed", "Not Tested"]
		customer_changelog_cursor: DF.Data | None
		enable_webhooks: DF.Check
		force_sync_customers: DF.Check
		force_sync_invoices: DF.Check
		force_sync_products: DF.Check
		force_sync_quotes: DF.Check
		invoice_changelog_cursor: DF.Data | None
		is_enabled: DF.Check
		last_connection_test: DF.Datetime | None
		log_retention_days: DF.Int
		notify_on_failure: DF.Check
		product_changelog_cursor: DF.Data | None
		quote_changelog_cursor: DF.Data | None
		sync_customers: DF.Check
		sync_from_date: DF.Date | None
		sync_invoices: DF.Check
		sync_products: DF.Check
		sync_quotes: DF.Check
		webhook_event_dms_file_created: DF.Check
		webhook_event_invoice_created: DF.Check
		webhook_event_quote_created: DF.Check
		webhook_registered_at: DF.Datetime | None
		webhook_secret: DF.Password | None
		webhook_subscription_id: DF.Data | None
		webhook_url: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if not self.base_url:
			self.base_url = "https://app.pennylane.com/api/external/v2"
		self.base_url = self.base_url.rstrip("/")

		if self.is_enabled and not self.company_id:
			frappe.msgprint(
				frappe._("Company ID is missing. Run <b>Test Connection</b> to populate it automatically."),
				indicator="orange",
				alert=True,
			)

		self.webhook_url = (
			frappe.utils.get_url("/api/method/pennylane.api.webhook.handle_webhook")
			if self.enable_webhooks
			else ""
		)

		try:
			self._handle_webhook_registration()
		except Exception as exc:
			frappe.log_error(str(exc), "Pennylane webhook registration failed")
			frappe.msgprint(
				frappe._("Webhook registration with Pennylane failed: {0}").format(str(exc)),
				indicator="orange",
				alert=True,
			)

	# ------------------------------------------------------------------
	# Webhook registration lifecycle
	# ------------------------------------------------------------------

	def _handle_webhook_registration(self):
		"""Register, update or unregister the Pennylane webhook subscription."""
		doc_before = self.get_doc_before_save()
		if not doc_before:
			return

		was_enabled = bool(doc_before.enable_webhooks)
		is_enabled = bool(self.enable_webhooks)

		if is_enabled and not was_enabled:
			# Toggle just switched ON → register
			self._register_webhook()

		elif not is_enabled and was_enabled:
			# Toggle just switched OFF → unregister
			self._unregister_webhook()

		elif is_enabled and was_enabled and self.webhook_subscription_id:
			# Still enabled — update events if they changed
			prev_events = _events_from_doc(doc_before)
			curr_events = self._get_selected_events()
			if set(prev_events) != set(curr_events):
				self._update_webhook()

	def _get_selected_events(self) -> list[str]:
		events = []
		if self.webhook_event_invoice_created:
			events.append("customer_invoice.created")
		if self.webhook_event_quote_created:
			events.append("quote.created")
		if self.webhook_event_dms_file_created:
			events.append("dms_file.created")
		return events

	def _register_webhook(self):
		"""Create the subscription on Pennylane and store the returned secret."""
		from pennylane.client.base import PennylaneClient
		from pennylane.client.webhooks import create_subscription

		events = self._get_selected_events()
		if not events:
			frappe.throw(frappe._("Select at least one event to subscribe to before enabling webhooks."))

		if not self.webhook_url:
			frappe.throw(frappe._("Webhook URL could not be determined. Make sure the site URL is configured."))

		client = PennylaneClient.from_settings()
		result = create_subscription(client, self.webhook_url, events)

		# Persist subscription ID immediately so it can be cleaned up even if the
		# surrounding save() fails and the in-memory fields are lost.
		frappe.db.set_value(
			"Pennylane Settings",
			"Pennylane Settings",
			{"webhook_subscription_id": str(result["id"]), "webhook_registered_at": frappe.utils.now_datetime()},
		)
		frappe.db.commit()

		# Secret is returned only once at creation — store it on self for the outer save.
		self.webhook_secret = result["secret"]
		self.webhook_subscription_id = result["id"]
		self.webhook_registered_at = frappe.utils.now_datetime()

	def _unregister_webhook(self):
		"""Delete the subscription from Pennylane."""
		from pennylane.client.base import PennylaneClient
		from pennylane.client.webhooks import delete_subscription

		try:
			client = PennylaneClient.from_settings()
			delete_subscription(client)
		except Exception as exc:
			frappe.log_error(str(exc), "Pennylane webhook unregister failed")
			frappe.msgprint(
				frappe._("Webhook unregistration failed: {0}. The subscription may still exist in Pennylane — use 'Re-register Webhook' to reconcile.").format(str(exc)),
				indicator="orange",
			)

		self.webhook_subscription_id = None
		self.webhook_registered_at = None
		# Keep webhook_secret in case the user re-enables (Pennylane will issue a new one anyway).

	def _update_webhook(self):
		"""Push the updated event list to Pennylane."""
		from pennylane.client.base import PennylaneClient
		from pennylane.client.webhooks import update_subscription

		events = self._get_selected_events()
		if not events:
			frappe.throw(frappe._("At least one subscribed event is required."))

		client = PennylaneClient.from_settings()
		update_subscription(client, events=events, enabled=True)

	# ------------------------------------------------------------------
	# Whitelisted actions (called from JS buttons)
	# ------------------------------------------------------------------

	@frappe.whitelist()
	def refresh_webhook_status(self):
		"""
		Fetch the current subscription from Pennylane and sync local state.
		Returns the subscription dict (without secret) or None.
		"""
		from pennylane.client.base import PennylaneClient
		from pennylane.client.webhooks import get_subscription

		client = PennylaneClient.from_settings()
		sub = get_subscription(client)

		if sub:
			self.webhook_subscription_id = sub["id"]
			self.webhook_registered_at = sub.get("created_at")
			# Sync event checkboxes from remote state
			remote_events = sub.get("events", [])
			self.webhook_event_invoice_created = int("customer_invoice.created" in remote_events)
			self.webhook_event_quote_created = int("quote.created" in remote_events)
			self.webhook_event_dms_file_created = int("dms_file.created" in remote_events)
		else:
			self.webhook_subscription_id = None
			self.webhook_registered_at = None

		self.save(ignore_permissions=True)
		return sub

	@frappe.whitelist()
	def reregister_webhook(self):
		"""Delete the existing subscription then create a fresh one."""
		from pennylane.client.base import PennylaneClient
		from pennylane.client.webhooks import create_subscription, delete_subscription

		client = PennylaneClient.from_settings()
		delete_subscription(client)

		events = self._get_selected_events()
		if not events:
			frappe.throw(frappe._("Select at least one event before re-registering."))

		result = create_subscription(client, self.webhook_url, events)

		self.webhook_secret = result["secret"]
		self.webhook_subscription_id = result["id"]
		self.webhook_registered_at = frappe.utils.now_datetime()
		self.save(ignore_permissions=True)

		return {"id": result["id"], "events": result.get("events", [])}

	# ------------------------------------------------------------------
	# Connection test
	# ------------------------------------------------------------------

	@frappe.whitelist()
	def test_connection(self):
		from pennylane.client.base import PennylaneClient

		try:
			client = PennylaneClient.from_settings()
			response = client.get("/me")
			self.connection_status = "Connected"
			company = response.get("company") or {}
			if company.get("id"):
				self.company_id = str(company["id"])
		except Exception as e:
			self.connection_status = "Failed"
			frappe.log_error(str(e), "Pennylane Connection Test")
		finally:
			self.last_connection_test = frappe.utils.now_datetime()
			self.save()

		return self.connection_status

	# ------------------------------------------------------------------
	# Force full sync
	# ------------------------------------------------------------------

	@frappe.whitelist()
	def run_full_sync(self):
		"""Enqueue a full re-import for each selected resource type."""
		frappe.only_for("System Manager")

		jobs = []

		if self.force_sync_customers:
			frappe.enqueue("pennylane.sync.customer.full_sync_customers", queue="long")
			jobs.append("customers")

		if self.force_sync_invoices:
			frappe.enqueue(
				"pennylane.sync.invoice.full_sync_invoices",
				queue="long",
				from_date=str(self.sync_from_date) if self.sync_from_date else None,
			)
			jobs.append("invoices")

		if self.force_sync_quotes:
			frappe.enqueue("pennylane.sync.quote.full_sync_quotes", queue="long")
			jobs.append("quotes")

		if self.force_sync_products:
			frappe.enqueue("pennylane.sync.product.full_sync_products", queue="long")
			jobs.append("products")

		self.force_sync_customers = 0
		self.force_sync_invoices = 0
		self.force_sync_quotes = 0
		self.force_sync_products = 0
		self.save()

		return {"queued": jobs}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _events_from_doc(doc) -> list[str]:
	"""Extract the selected event list from a settings document."""
	events = []
	if doc.webhook_event_invoice_created:
		events.append("customer_invoice.created")
	if doc.webhook_event_quote_created:
		events.append("quote.created")
	if doc.webhook_event_dms_file_created:
		events.append("dms_file.created")
	return events
