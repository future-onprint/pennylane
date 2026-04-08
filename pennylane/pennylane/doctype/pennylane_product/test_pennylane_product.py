# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from pennylane.mappers.product import from_pennylane, to_pennylane

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_product(**kwargs) -> "frappe.Document":
	defaults = {"label": "_Test Product"}
	defaults.update(kwargs)
	doc = frappe.new_doc("Pennylane Product")
	doc.update(defaults)
	doc.insert(ignore_permissions=True)
	return doc


class IntegrationTestPennylaneProduct(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Pennylane Product", {"label": ["like", "_Test%"]})
		frappe.db.commit()

	# ------------------------------------------------------------------
	# DocType
	# ------------------------------------------------------------------

	def test_create_minimal(self):
		doc = make_product(label="_Test Minimal")
		self.assertEqual(doc.label, "_Test Minimal")
		self.assertEqual(doc.sync_status, "Pending")

	def test_create_with_all_fields(self):
		doc = make_product(
			label="_Test Full",
			reference="REF-001",
			unit="hour",
			vat_rate="FR_200",
			currency_amount=100.0,
			description="A test product",
			external_reference="EXT-001",
		)
		self.assertEqual(doc.reference, "REF-001")
		self.assertEqual(doc.unit, "hour")
		self.assertEqual(doc.vat_rate, "FR_200")

	# ------------------------------------------------------------------
	# Mapper — to_pennylane
	# ------------------------------------------------------------------

	def test_to_pennylane_minimal(self):
		doc = make_product(label="_Test Mapper")
		payload = to_pennylane(doc.name)
		self.assertEqual(payload["label"], "_Test Mapper")
		self.assertNotIn("reference", payload)
		self.assertNotIn("unit", payload)

	def test_to_pennylane_with_optional_fields(self):
		doc = make_product(
			label="_Test Optional",
			reference="REF-002",
			unit="piece",
			vat_rate="FR_100",
			currency_amount=50.0,
			description="desc",
			external_reference="EXT-002",
		)
		payload = to_pennylane(doc.name)
		self.assertEqual(payload["reference"], "REF-002")
		self.assertEqual(payload["unit"], "piece")
		self.assertEqual(payload["vat_rate"], "FR_100")
		self.assertEqual(payload["currency_amount"], "50.0")
		self.assertEqual(payload["description"], "desc")
		self.assertEqual(payload["external_reference"], "EXT-002")

	# ------------------------------------------------------------------
	# Mapper — from_pennylane
	# ------------------------------------------------------------------

	def test_from_pennylane_basic(self):
		pl = {
			"id": 123,
			"label": "Widget",
			"reference": "W-001",
			"unit": "piece",
			"vat_rate": "FR_200",
			"currency_amount": "9.99",
			"description": "A widget",
		}
		fields = from_pennylane(pl)
		self.assertEqual(fields["label"], "Widget")
		self.assertEqual(fields["pennylane_id"], 123)
		self.assertEqual(fields["reference"], "W-001")
		self.assertEqual(fields["unit"], "piece")
		self.assertEqual(fields["currency_amount"], "9.99")

	def test_from_pennylane_missing_optional_fields(self):
		pl = {"id": 456, "label": "_Test Sparse"}
		fields = from_pennylane(pl)
		self.assertEqual(fields["label"], "_Test Sparse")
		self.assertIsNone(fields["reference"])
		self.assertIsNone(fields["unit"])
		self.assertIsNone(fields["description"])
