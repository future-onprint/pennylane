import frappe
from frappe.model.document import Document


class PennylaneSyncLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		direction: DF.Literal["push", "pull"]
		error_message: DF.SmallText | None
		frappe_docname: DF.Data | None
		frappe_doctype: DF.Data | None
		http_status_code: DF.Int
		operation: DF.Literal["create", "update", "delete"]
		pennylane_id: DF.Data | None
		request_payload: DF.Code | None
		resource_type: DF.Literal["customer"]
		response_payload: DF.Code | None
		retry_count: DF.Int
		status: DF.Literal["Success", "Failed", "Pending"]
	# end: auto-generated types

	pass
