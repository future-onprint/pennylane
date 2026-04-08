# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from pennylane.sync.utils import write_log

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPennylaneSyncLog(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Pennylane Sync Log", {"frappe_docname": ["like", "_Test%"]})
		frappe.db.commit()

	def test_write_log_success(self):
		write_log(
			direction="push",
			resource_type="customer",
			operation="create",
			status="Success",
			frappe_doctype="Pennylane Customer",
			frappe_docname="_Test Customer",
			pennylane_id=42,
			request_payload={"name": "_Test Customer"},
			response_payload={"id": 42},
		)
		log = frappe.get_last_doc("Pennylane Sync Log", filters={"frappe_docname": "_Test Customer"})
		self.assertEqual(log.direction, "push")
		self.assertEqual(log.resource_type, "customer")
		self.assertEqual(log.operation, "create")
		self.assertEqual(log.status, "Success")
		self.assertEqual(log.pennylane_id, "42")

	def test_write_log_failure(self):
		write_log(
			direction="push",
			resource_type="customer",
			operation="update",
			status="Failed",
			frappe_doctype="Pennylane Customer",
			frappe_docname="_Test Customer Failed",
			error_message="Connection timeout",
			http_status_code=503,
		)
		log = frappe.get_last_doc("Pennylane Sync Log", filters={"frappe_docname": "_Test Customer Failed"})
		self.assertEqual(log.status, "Failed")
		self.assertEqual(log.error_message, "Connection timeout")
		self.assertEqual(log.http_status_code, 503)

	def test_log_is_readonly(self):
		meta = frappe.get_meta("Pennylane Sync Log")
		# Logs should not expose write permissions beyond System Manager
		roles_with_write = [p.role for p in meta.permissions if p.write]
		self.assertNotIn("All", roles_with_write)
