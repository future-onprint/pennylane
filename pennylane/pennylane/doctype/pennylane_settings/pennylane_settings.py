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
		connection_status: DF.Literal["", "Connected", "Failed", "Not Tested"]
		customer_changelog_cursor: DF.Data | None
		force_sync_customers: DF.Check
		force_sync_invoices: DF.Check
		force_sync_products: DF.Check
		force_sync_quotes: DF.Check
		invoice_changelog_cursor: DF.Data | None
		is_enabled: DF.Check
		last_connection_test: DF.Datetime | None
		notify_on_failure: DF.Check
		product_changelog_cursor: DF.Data | None
		quote_changelog_cursor: DF.Data | None
		sync_customers: DF.Check
		sync_invoices: DF.Check
		sync_products: DF.Check
		sync_quotes: DF.Check
		webhook_secret: DF.Password | None
	# end: auto-generated types

	def validate(self):
		if not self.base_url:
			self.base_url = "https://app.pennylane.com/api/external/v2"
		self.base_url = self.base_url.rstrip("/")

	@frappe.whitelist()
	def test_connection(self):
		from pennylane.client.base import PennylaneClient

		try:
			client = PennylaneClient.from_settings()
			client.get("/me")
			self.connection_status = "Connected"
		except Exception as e:
			self.connection_status = "Failed"
			frappe.log_error(str(e), "Pennylane Connection Test")
		finally:
			self.last_connection_test = frappe.utils.now_datetime()
			self.save()

		return self.connection_status

	@frappe.whitelist()
	def run_full_sync(self):
		"""Enqueue a full re-import for each selected resource type."""
		frappe.only_for("System Manager")

		jobs = []

		if self.force_sync_customers:
			frappe.enqueue("pennylane.sync.customer.full_sync_customers", queue="long")
			jobs.append("customers")

		if self.force_sync_invoices:
			frappe.enqueue("pennylane.sync.invoice.full_sync_invoices", queue="long")
			jobs.append("invoices")

		if self.force_sync_quotes:
			frappe.enqueue("pennylane.sync.quote.full_sync_quotes", queue="long")
			jobs.append("quotes")

		if self.force_sync_products:
			frappe.enqueue("pennylane.sync.product.full_sync_products", queue="long")
			jobs.append("products")

		# Reset checkboxes after enqueueing
		self.force_sync_customers = 0
		self.force_sync_invoices = 0
		self.force_sync_quotes = 0
		self.force_sync_products = 0
		self.save()

		return {"queued": jobs}
