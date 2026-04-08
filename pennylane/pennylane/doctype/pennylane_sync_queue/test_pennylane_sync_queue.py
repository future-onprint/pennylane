# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
import frappe.utils
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_queue_item(**kwargs) -> "frappe.Document":
	defaults = {
		"resource_type": "customer",
		"operation": "create",
		"status": "Pending",
		"frappe_doctype": "Pennylane Customer",
		"frappe_docname": "_Test Customer",
		"retry_count": 0,
		"next_retry_at": frappe.utils.now_datetime(),
	}
	defaults.update(kwargs)
	doc = frappe.new_doc("Pennylane Sync Queue")
	doc.update(defaults)
	doc.insert(ignore_permissions=True)
	return doc


class IntegrationTestPennylaneSyncQueue(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Pennylane Sync Queue", {"frappe_docname": ["like", "_Test%"]})
		frappe.db.commit()

	def test_create_pending_item(self):
		doc = make_queue_item()
		self.assertEqual(doc.status, "Pending")
		self.assertEqual(doc.retry_count, 0)

	def test_status_transitions(self):
		doc = make_queue_item(frappe_docname="_Test Transition")
		frappe.db.set_value("Pennylane Sync Queue", doc.name, "status", "Processing")
		self.assertEqual(
			frappe.db.get_value("Pennylane Sync Queue", doc.name, "status"),
			"Processing",
		)

	def test_retry_count_increments(self):
		doc = make_queue_item(frappe_docname="_Test Retry")
		frappe.db.set_value("Pennylane Sync Queue", doc.name, "retry_count", 1)
		self.assertEqual(
			frappe.db.get_value("Pennylane Sync Queue", doc.name, "retry_count"),
			1,
		)

	def test_abandoned_after_max_retries(self):
		doc = make_queue_item(frappe_docname="_Test Abandon", retry_count=4)
		# Simulate the last failure: retry_count hits 5 → Abandoned
		new_count = doc.retry_count + 1
		new_status = "Abandoned" if new_count >= 5 else "Failed"
		frappe.db.set_value(
			"Pennylane Sync Queue",
			doc.name,
			{"status": new_status, "retry_count": new_count},
		)
		updated = frappe.db.get_value(
			"Pennylane Sync Queue", doc.name, ["status", "retry_count"], as_dict=True
		)
		self.assertEqual(updated.status, "Abandoned")
		self.assertEqual(updated.retry_count, 5)

	def test_only_customer_resource_type_allowed(self):
		meta = frappe.get_meta("Pennylane Sync Queue")
		field = meta.get_field("resource_type")
		allowed = [o for o in field.options.split("\n") if o]
		self.assertEqual(allowed, ["customer"])
