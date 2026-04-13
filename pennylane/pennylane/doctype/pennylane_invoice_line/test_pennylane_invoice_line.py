# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from pennylane.mappers.invoice_line import lines_from_pennylane, lines_to_pennylane

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def _make_line(**kwargs):
	"""Return a plain object mimicking a child table row (not persisted)."""
	defaults = {
		"label": "_Test Line",
		"quantity": 1.0,
		"unit_price": 10.0,
		"discount_type": "relative",
		"discount": 0.0,
		"currency_amount": 0.0,
		"product": None,
		"vat_rate": None,
		"unit": None,
		"description": None,
	}
	defaults.update(kwargs)
	return frappe._dict(defaults)


class IntegrationTestPennylaneInvoiceLine(IntegrationTestCase):
	# ------------------------------------------------------------------
	# currency_amount calculation (before_save logic)
	# ------------------------------------------------------------------

	def test_currency_amount_no_discount(self):
		line = frappe.new_doc("Pennylane Invoice Line")
		line.label = "_Test"
		line.quantity = 3.0
		line.unit_price = 10.0
		line.discount_type = "relative"
		line.discount = 0.0
		line.before_save()
		self.assertAlmostEqual(line.currency_amount, 30.0)

	def test_currency_amount_relative_discount(self):
		line = frappe.new_doc("Pennylane Invoice Line")
		line.label = "_Test Disc"
		line.quantity = 2.0
		line.unit_price = 100.0
		line.discount_type = "relative"
		line.discount = 25.0
		line.before_save()
		self.assertAlmostEqual(line.currency_amount, 150.0)

	def test_currency_amount_absolute_discount(self):
		line = frappe.new_doc("Pennylane Invoice Line")
		line.label = "_Test Abs"
		line.quantity = 2.0
		line.unit_price = 100.0
		line.discount_type = "absolute"
		line.discount = 30.0
		line.before_save()
		self.assertAlmostEqual(line.currency_amount, 170.0)

	def test_currency_amount_zero_quantity(self):
		line = frappe.new_doc("Pennylane Invoice Line")
		line.label = "_Test Zero"
		line.quantity = 0.0
		line.unit_price = 50.0
		line.discount_type = "relative"
		line.discount = 0.0
		line.before_save()
		self.assertAlmostEqual(line.currency_amount, 0.0)

	# ------------------------------------------------------------------
	# Mapper — lines_to_pennylane
	# ------------------------------------------------------------------

	def test_lines_to_pennylane_free_text_line(self):
		lines = [_make_line(label="Service", quantity=2.0, unit_price=50.0, currency_amount=100.0)]
		payload = lines_to_pennylane(lines)
		self.assertEqual(len(payload), 1)
		self.assertEqual(payload[0]["label"], "Service")
		self.assertEqual(payload[0]["quantity"], 2.0)
		self.assertEqual(payload[0]["raw_currency_unit_price"], "50.0")
		self.assertNotIn("product_id", payload[0])

	def test_lines_to_pennylane_omits_empty_optional(self):
		lines = [_make_line()]
		payload = lines_to_pennylane(lines)
		self.assertNotIn("vat_rate", payload[0])
		self.assertNotIn("unit", payload[0])
		self.assertNotIn("description", payload[0])
		self.assertNotIn("discount", payload[0])

	def test_lines_to_pennylane_relative_discount(self):
		lines = [_make_line(vat_rate="FR_200", unit="hour", discount_type="relative", discount=10.0)]
		payload = lines_to_pennylane(lines)
		self.assertEqual(payload[0]["vat_rate"], "FR_200")
		self.assertEqual(payload[0]["unit"], "hour")
		self.assertEqual(payload[0]["discount"], {"type": "relative", "value": "10.0"})

	def test_lines_to_pennylane_absolute_discount(self):
		lines = [_make_line(discount_type="absolute", discount=25.0)]
		payload = lines_to_pennylane(lines)
		self.assertEqual(payload[0]["discount"], {"type": "absolute", "value": "25.0"})

	def test_lines_to_pennylane_multiple_lines(self):
		lines = [
			_make_line(label="Line A", quantity=1.0, unit_price=10.0),
			_make_line(label="Line B", quantity=3.0, unit_price=20.0),
		]
		payload = lines_to_pennylane(lines)
		self.assertEqual(len(payload), 2)
		self.assertEqual(payload[1]["label"], "Line B")

	# ------------------------------------------------------------------
	# Mapper — lines_from_pennylane
	# ------------------------------------------------------------------

	def test_lines_from_pennylane_basic(self):
		pl_lines = [
			{
				"label": "Service",
				"quantity": "2",
				"raw_currency_unit_price": "75.00",
				"vat_rate": "FR_200",
				"currency_amount": "150.00",
			}
		]
		rows = lines_from_pennylane(pl_lines)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["label"], "Service")
		self.assertAlmostEqual(rows[0]["quantity"], 2.0)
		self.assertAlmostEqual(rows[0]["unit_price"], 75.0)
		self.assertEqual(rows[0]["vat_rate"], "FR_200")
		self.assertIsNone(rows[0]["product"])

	def test_lines_from_pennylane_parses_discount_object(self):
		pl_lines = [
			{
				"label": "Item",
				"quantity": "1",
				"raw_currency_unit_price": "100.00",
				"discount": {"type": "relative", "value": "20"},
			}
		]
		rows = lines_from_pennylane(pl_lines)
		self.assertEqual(rows[0]["discount_type"], "relative")
		self.assertAlmostEqual(rows[0]["discount"], 20.0)

	def test_lines_from_pennylane_defaults_quantity_to_one(self):
		pl_lines = [{"label": "Item", "raw_currency_unit_price": "10.00"}]
		rows = lines_from_pennylane(pl_lines)
		self.assertAlmostEqual(rows[0]["quantity"], 1.0)

	def test_lines_from_pennylane_empty_list(self):
		self.assertEqual(lines_from_pennylane([]), [])
