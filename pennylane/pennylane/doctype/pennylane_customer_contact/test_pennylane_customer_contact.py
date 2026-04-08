# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPennylaneCustomerContact(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Pennylane Customer", {"customer_name": ["like", "_Test%"]})
		frappe.db.commit()

	def _make_customer(self, name="_Test Contact Customer") -> "frappe.Document":
		doc = frappe.new_doc("Pennylane Customer")
		doc.customer_name = name
		doc.customer_type = "company"
		doc.insert(ignore_permissions=True)
		return doc

	def test_contacts_child_table_exists(self):
		"""Pennylane Customer should have a contacts child table field."""
		customer = self._make_customer()
		self.assertTrue(hasattr(customer, "contacts"))
		self.assertEqual(customer.contacts, [])

	def test_add_contact_row(self):
		"""Adding a contact row to the child table should persist correctly."""
		customer = self._make_customer("_Test Contact Customer 2")
		customer.append("contacts", {
			"pennylane_id": 1001,
			"first_name": "Alice",
			"last_name": "Martin",
			"role": "billing",
			"email": "alice@example.com",
			"telephone_number": "+33123456789",
			"mobile_number": "+33612345678",
		})
		customer.save(ignore_permissions=True)
		customer.reload()

		self.assertEqual(len(customer.contacts), 1)
		contact = customer.contacts[0]
		self.assertEqual(contact.pennylane_id, 1001)
		self.assertEqual(contact.first_name, "Alice")
		self.assertEqual(contact.email, "alice@example.com")
