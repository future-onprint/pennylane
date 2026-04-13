from frappe.model.document import Document


class PennylaneCustomerInvoice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from pennylane.pennylane.doctype.pennylane_invoice_line.pennylane_invoice_line import PennylaneInvoiceLine

		amended_from: DF.Link | None
		amount: DF.Currency
		currency: DF.Link | None
		currency_amount: DF.Currency
		customer: DF.Link
		date: DF.Date
		deadline: DF.Date
		external_reference: DF.Data | None
		invoice_lines: DF.Table[PennylaneInvoiceLine]
		invoice_number: DF.Data | None
		label: DF.Data | None
		language: DF.Literal["", "fr_FR", "en_GB", "de_DE"]
		last_synced_at: DF.Datetime | None
		pdf_description: DF.SmallText | None
		pdf_invoice_free_text: DF.SmallText | None
		pdf_invoice_subject: DF.Data | None
		pennylane_id: DF.Data | None
		source_quote: DF.Link | None
		special_mention: DF.SmallText | None
		status: DF.Literal["draft", "incomplete", "upcoming", "late", "paid", "partially_paid", "partially_cancelled", "cancelled", "credit_note", "archived", "proforma"]
		sync_status: DF.Literal["Pending", "Synced", "Failed", "Deleted"]
	# end: auto-generated types

	pass
