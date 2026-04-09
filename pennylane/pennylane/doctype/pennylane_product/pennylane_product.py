from frappe.model.document import Document


class PennylaneProduct(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		unit_price: DF.Currency
		description: DF.SmallText | None
		external_reference: DF.Data | None
		label: DF.Data
		last_synced_at: DF.Datetime | None
		pennylane_id: DF.Int
		price: DF.Currency
		reference: DF.Data | None
		sync_status: DF.Literal["Pending", "Synced", "Failed", "Deleted"]
		unit: DF.Link | None
		vat_rate: DF.Link | None
	# end: auto-generated types

	pass
