# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from pennylane.install import _VAT_RATE_CODES, _seed_vat_rates

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPennylaneVATRate(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_seed_vat_rates()

	# ------------------------------------------------------------------
	# Seeding
	# ------------------------------------------------------------------

	def test_seed_creates_all_rates(self):
		codes = frappe.db.get_all("Pennylane VAT Rate", pluck="name")
		for expected in _VAT_RATE_CODES:
			self.assertIn(expected, codes, msg=f"{expected} missing after seeding")

	def test_seeding_is_idempotent(self):
		"""Calling _seed_vat_rates twice must not raise or create duplicates."""
		_seed_vat_rates()
		count = frappe.db.count("Pennylane VAT Rate")
		self.assertEqual(count, len(_VAT_RATE_CODES))

	# ------------------------------------------------------------------
	# Field values
	# ------------------------------------------------------------------

	def test_fr_200_fields(self):
		doc = frappe.get_doc("Pennylane VAT Rate", "FR_200")
		self.assertEqual(doc.code, "FR_200")
		self.assertEqual(doc.rate, 20.0)
		self.assertEqual(doc.is_exempt, 0)
		self.assertIn("20", doc.label)

	def test_fr_55_fields(self):
		doc = frappe.get_doc("Pennylane VAT Rate", "FR_55")
		self.assertEqual(doc.rate, 5.5)
		self.assertEqual(doc.is_exempt, 0)

	def test_exempt_is_flagged(self):
		doc = frappe.get_doc("Pennylane VAT Rate", "exempt")
		self.assertEqual(doc.rate, 0.0)
		self.assertEqual(doc.is_exempt, 1)

	def test_fr_0_is_not_exempt(self):
		"""FR_0 (zero-rated exports) is distinct from exonerated."""
		doc = frappe.get_doc("Pennylane VAT Rate", "FR_0")
		self.assertEqual(doc.rate, 0.0)
		self.assertEqual(doc.is_exempt, 0)

	def test_title_field_is_label(self):
		meta = frappe.get_meta("Pennylane VAT Rate")
		self.assertEqual(meta.title_field, "label")

	# ------------------------------------------------------------------
	# Immutability
	# ------------------------------------------------------------------

	def test_cannot_modify_existing_rate(self):
		doc = frappe.get_doc("Pennylane VAT Rate", "FR_200")
		doc.label = "Hacked label"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_cannot_delete_rate(self):
		with self.assertRaises(Exception):
			frappe.delete_doc(
				"Pennylane VAT Rate", "FR_200", ignore_permissions=False, force=False
			)
