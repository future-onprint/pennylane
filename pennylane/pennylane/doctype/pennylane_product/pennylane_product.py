from frappe.model.document import Document


class PennylaneProduct(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency_amount: DF.Currency
		description: DF.SmallText | None
		external_reference: DF.Data | None
		label: DF.Data
		last_synced_at: DF.Datetime | None
		pennylane_id: DF.Int
		reference: DF.Data | None
		sync_status: DF.Literal["Pending", "Synced", "Failed"]
		unit: DF.Data | None
		vat_rate: DF.Data | None
	# end: auto-generated types

	pass
