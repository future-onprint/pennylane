import frappe
from frappe.model.document import Document


class PennylaneSyncQueue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		frappe_docname: DF.Data
		frappe_doctype: DF.Data
		next_retry_at: DF.Datetime | None
		operation: DF.Literal["create", "update", "delete"]
		payload: DF.Code | None
		pennylane_id: DF.Data | None
		resource_type: DF.Literal["customer"]
		retry_count: DF.Int
		status: DF.Literal["Pending", "Processing", "Failed", "Abandoned"]
	# end: auto-generated types

	pass
