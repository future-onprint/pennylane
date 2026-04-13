# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

from frappe.model.document import Document


class PennylaneCustomerContact(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		email: DF.Data | None
		first_name: DF.Data | None
		last_name: DF.Data | None
		mobile_number: DF.Data | None
		pennylane_id: DF.Int
		role: DF.Data | None
		telephone_number: DF.Data | None
	# end: auto-generated types

	pass
