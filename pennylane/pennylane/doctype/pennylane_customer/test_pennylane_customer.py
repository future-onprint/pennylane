# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from pennylane.mappers.customer import from_pennylane, to_pennylane

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_customer(**kwargs) -> "frappe.Document":
	defaults = {"customer_name": "_Test Customer", "customer_type": "company"}
	defaults.update(kwargs)
	doc = frappe.new_doc("Pennylane Customer")
	doc.update(defaults)
	doc.insert(ignore_permissions=True)
	return doc


class IntegrationTestPennylaneCustomer(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Pennylane Customer", {"customer_name": ["like", "_Test%"]})
		frappe.db.commit()

	# ------------------------------------------------------------------
	# DocType
	# ------------------------------------------------------------------

	def test_create_minimal(self):
		doc = make_customer(customer_name="_Test Minimal")
		self.assertEqual(doc.customer_type, "company")
		self.assertEqual(doc.sync_status, "Pending")

	def test_duplicate_name_raises(self):
		make_customer(customer_name="_Test Duplicate")
		with self.assertRaises(frappe.DuplicateEntryError):
			make_customer(customer_name="_Test Duplicate")

	def test_individual_type_allowed(self):
		doc = make_customer(customer_name="_Test Individual", customer_type="individual")
		self.assertEqual(doc.customer_type, "individual")

	# ------------------------------------------------------------------
	# Mapper — to_pennylane
	# ------------------------------------------------------------------

	def test_to_pennylane_basic(self):
		doc = make_customer(
			customer_name="_Test Acme",
			email="acme@example.com",
			phone="+33123456789",
		)
		payload = to_pennylane(doc.name)
		self.assertEqual(payload["name"], "_Test Acme")
		self.assertEqual(payload["customer_type"], "company")
		self.assertEqual(payload["emails"], ["acme@example.com"])
		self.assertEqual(payload["phone"], "+33123456789")

	def test_to_pennylane_omits_empty_optional_fields(self):
		doc = make_customer(customer_name="_Test Sparse")
		payload = to_pennylane(doc.name)
		self.assertNotIn("emails", payload)
		self.assertNotIn("phone", payload)
		self.assertNotIn("vat_number", payload)
		self.assertNotIn("address", payload)

	def test_to_pennylane_address_block(self):
		doc = make_customer(
			customer_name="_Test Addr",
			address_line1="12 Rue de la Paix",
			postal_code="75001",
			city="Paris",
			country="France",
		)
		payload = to_pennylane(doc.name)
		self.assertIn("address", payload)
		self.assertEqual(payload["address"]["city"], "Paris")
		self.assertEqual(payload["address"]["postal_code"], "75001")
		self.assertEqual(payload["address"]["country_alpha2"], "FR")

	def test_to_pennylane_tax_fields(self):
		doc = make_customer(
			customer_name="_Test Tax",
			vat_number="FR12345678901",
			siren="123456789",
			siret="12345678900012",
		)
		payload = to_pennylane(doc.name)
		self.assertEqual(payload["vat_number"], "FR12345678901")
		self.assertEqual(payload["siren"], "123456789")
		self.assertEqual(payload["siret"], "12345678900012")

	# ------------------------------------------------------------------
	# Mapper — from_pennylane
	# ------------------------------------------------------------------

	def test_from_pennylane_company(self):
		pl = {
			"id": 42,
			"name": "Acme Corp",
			"customer_type": "company",
			"emails": ["acme@example.com"],
			"phone": "+33600000000",
			"vat_number": "FR00123456789",
			"address": {
				"address": "1 rue Test",
				"postal_code": "75000",
				"city": "Paris",
				"country_alpha2": "FR",
			},
		}
		fields = from_pennylane(pl)
		self.assertEqual(fields["customer_name"], "Acme Corp")
		self.assertEqual(fields["pennylane_id"], 42)
		self.assertEqual(fields["email"], "acme@example.com")
		self.assertEqual(fields["city"], "Paris")
		self.assertEqual(fields["vat_number"], "FR00123456789")

	def test_from_pennylane_individual_name_composed(self):
		pl = {
			"id": 99,
			"first_name": "Jean",
			"last_name": "Dupont",
			"customer_type": "individual",
			"emails": [],
		}
		fields = from_pennylane(pl)
		self.assertEqual(fields["customer_name"], "Jean Dupont")
		self.assertEqual(fields["customer_type"], "individual")

	def test_from_pennylane_empty_emails(self):
		pl = {"id": 1, "name": "Empty Co", "emails": []}
		fields = from_pennylane(pl)
		self.assertIsNone(fields["email"])

	def test_from_pennylane_resolves_country(self):
		pl = {
			"id": 7,
			"name": "French Co",
			"address": {"country_alpha2": "FR", "city": "Lyon"},
		}
		fields = from_pennylane(pl)
		if fields["country"]:
			self.assertEqual(fields["country"], "France")
