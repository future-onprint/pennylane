# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.model.document import Document


class PennylaneUnit(Document):
	def before_save(self):
		if not self.is_new():
			frappe.throw(frappe._("Units are managed by the system and cannot be modified."))
