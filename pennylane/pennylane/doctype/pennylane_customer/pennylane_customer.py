import frappe
from frappe.model.document import Document


class PennylaneCustomer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from pennylane.pennylane.doctype.pennylane_customer_contact.pennylane_customer_contact import PennylaneCustomerContact

		address_line1: DF.Data | None
		billing_iban: DF.Data | None
		billing_language: DF.Link | None
		city: DF.Data | None
		contacts: DF.Table[PennylaneCustomerContact]
		country: DF.Link | None
		customer_name: DF.Data
		customer_type: DF.Literal["company", "individual"]
		delivery_address_line1: DF.Data | None
		delivery_city: DF.Data | None
		delivery_country: DF.Link | None
		delivery_postal_code: DF.Data | None
		email: DF.Data | None
		external_reference: DF.Data | None
		first_name: DF.Data | None
		last_name: DF.Data | None
		last_synced_at: DF.Datetime | None
		ledger_account_number: DF.Data | None
		notes: DF.SmallText | None
		payment_conditions: DF.Literal["upon_receipt", "custom", "7_days", "15_days", "30_days", "30_days_end_of_month", "45_days", "45_days_end_of_month", "60_days"]
		pennylane_id: DF.Data | None
		phone: DF.Data | None
		postal_code: DF.Data | None
		recipient: DF.Data | None
		reference: DF.Data | None
		reg_no: DF.Data | None
		sync_status: DF.Literal["Pending", "Synced", "Failed", "Deleted"]
		vat_number: DF.Data | None
	# end: auto-generated types

	def before_save(self):
		if self.customer_type == "individual":
			full = f"{self.first_name or ''} {self.last_name or ''}".strip()
			if full:
				self.customer_name = full
