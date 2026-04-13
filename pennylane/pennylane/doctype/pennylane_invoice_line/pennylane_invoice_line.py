from frappe.model.document import Document


class PennylaneInvoiceLine(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		currency_amount: DF.Currency
		description: DF.SmallText | None
		discount: DF.Float
		discount_type: DF.Literal["relative", "absolute"]
		label: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		product: DF.Link | None
		quantity: DF.Float
		unit: DF.Link | None
		unit_price: DF.Currency
		vat_rate: DF.Link | None
	# end: auto-generated types

	def before_save(self):
		qty = float(self.quantity or 0)
		price = float(self.unit_price or 0)
		discount = float(self.discount or 0)

		if (self.discount_type or "relative") == "absolute":
			self.currency_amount = round(qty * price - discount, 2)
		else:
			self.currency_amount = round(qty * price * (1 - discount / 100), 2)
