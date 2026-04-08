import frappe
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
		invoice_changelog_cursor: DF.Data | None
		is_enabled: DF.Check
		last_connection_test: DF.Datetime | None
		quote_changelog_cursor: DF.Data | None
		sync_customers: DF.Check
		sync_invoices: DF.Check
		sync_quotes: DF.Check
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
			import frappe.utils

			self.last_connection_test = frappe.utils.now_datetime()
			self.save()

		return self.connection_status
