# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.model.document import Document


class PennylaneUnit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		code: DF.Data
		label: DF.Data
		symbol: DF.Data | None
	# end: auto-generated types

	def before_save(self):
		if not self.is_new():
			frappe.throw(frappe._("Units are managed by the system and cannot be modified."))
