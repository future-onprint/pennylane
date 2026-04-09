import frappe
from frappe.model.document import Document


class PennylaneVATRate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		code: DF.Data | None
		description: DF.SmallText | None
		is_exempt: DF.Check
		label: DF.Data
		rate: DF.Percent
	# end: auto-generated types

	def before_save(self):
		if not self.is_new():
			frappe.throw(frappe._("VAT Rates are managed by the system and cannot be modified."))
