# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from pennylane.mappers.quote import from_pennylane, to_pennylane

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_customer(**kwargs) -> "frappe.Document":
	defaults = {"customer_name": "_Test Quote Customer", "customer_type": "company"}
	defaults.update(kwargs)
	doc = frappe.new_doc("Pennylane Customer")
	doc.update(defaults)
	doc.insert(ignore_permissions=True)
	return doc


def make_quote(customer_name: str, **kwargs) -> "frappe.Document":
	defaults = {
		"customer": customer_name,
		"date": "2026-02-01",
		"deadline": "2026-03-01",
		"invoice_lines": [
			{"label": "_Test Item", "quantity": 1.0, "unit_price": 200.0},
		],
	}
	defaults.update(kwargs)
	doc = frappe.new_doc("Pennylane Customer Quote")
	doc.update(defaults)
	doc.insert(ignore_permissions=True)
	return doc


class IntegrationTestPennylaneCustomerQuote(IntegrationTestCase):
	def setUp(self):
		self.customer = make_customer()

	def tearDown(self):
		frappe.db.delete("Pennylane Customer Quote", {"customer": ["like", "_Test%"]})
		frappe.db.delete("Pennylane Customer", {"customer_name": ["like", "_Test%"]})
		frappe.db.commit()

	# ------------------------------------------------------------------
	# DocType
	# ------------------------------------------------------------------

	def test_create_minimal(self):
		quote = make_quote(self.customer.name)
		self.assertEqual(quote.customer, self.customer.name)
		self.assertEqual(quote.status, "pending")
		self.assertEqual(quote.sync_status, "Pending")
		self.assertEqual(quote.currency, "EUR")
		self.assertEqual(quote.docstatus, 0)

	def test_create_with_lines(self):
		quote = make_quote(
			self.customer.name,
			invoice_lines=[
				{"label": "Line 1", "quantity": 5.0, "unit_price": 20.0},
				{"label": "Line 2", "quantity": 1.0, "unit_price": 500.0},
			],
		)
		self.assertEqual(len(quote.invoice_lines), 2)
		self.assertEqual(quote.invoice_lines[1].label, "Line 2")

	def test_create_with_deadline(self):
		quote = make_quote(self.customer.name, deadline="2026-04-01")
		self.assertEqual(quote.deadline, frappe.utils.getdate("2026-04-01"))

	# ------------------------------------------------------------------
	# Mapper — to_pennylane
	# ------------------------------------------------------------------

	def test_to_pennylane_basic(self):
		self.customer.pennylane_id = 55
		self.customer.save(ignore_permissions=True)

		quote = make_quote(self.customer.name)
		payload = to_pennylane(quote.name)

		self.assertEqual(payload["date"], "2026-02-01")
		self.assertEqual(payload["deadline"], "2026-03-01")
		self.assertEqual(payload["customer_id"], 55)
		self.assertIn("invoice_lines", payload)
		self.assertEqual(len(payload["invoice_lines"]), 1)

	def test_to_pennylane_includes_optional_fields(self):
		self.customer.pennylane_id = 56
		self.customer.save(ignore_permissions=True)

		quote = make_quote(
			self.customer.name,
			currency="GBP",
			language="en_GB",
			external_reference="QUOTE-EXT-1",
			pdf_invoice_subject="Quotation",
			special_mention="Valid 30 days",
		)
		payload = to_pennylane(quote.name)
		self.assertEqual(payload["currency"], "GBP")
		self.assertEqual(payload["language"], "en_GB")
		self.assertEqual(payload["external_reference"], "QUOTE-EXT-1")
		self.assertEqual(payload["pdf_invoice_subject"], "Quotation")
		self.assertEqual(payload["special_mention"], "Valid 30 days")

	def test_to_pennylane_omits_missing_optional(self):
		self.customer.pennylane_id = 57
		self.customer.save(ignore_permissions=True)

		quote = make_quote(self.customer.name)
		payload = to_pennylane(quote.name)
		self.assertNotIn("external_reference", payload)
		self.assertNotIn("language", payload)

	# ------------------------------------------------------------------
	# Mapper — from_pennylane
	# ------------------------------------------------------------------

	def test_from_pennylane_resolves_customer(self):
		self.customer.pennylane_id = 200
		self.customer.save(ignore_permissions=True)

		pl_quote = {
			"id": 501,
			"date": "2026-02-10",
			"deadline": "2026-03-10",
			"status": "accepted",
			"currency": "EUR",
			"customer": {"id": 200},
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_quote)
		self.assertEqual(fields["pennylane_id"], 501)
		self.assertEqual(fields["customer"], self.customer.name)
		self.assertEqual(fields["status"], "accepted")
		self.assertTrue(fields["_locked"])

	def test_from_pennylane_pending_is_not_locked(self):
		pl_quote = {
			"id": 502,
			"date": "2026-02-10",
			"deadline": "2026-03-10",
			"status": "pending",
			"customer": None,
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_quote)
		self.assertFalse(fields["_locked"])

	def test_from_pennylane_unknown_customer_is_none(self):
		pl_quote = {
			"id": 503,
			"date": "2026-02-10",
			"deadline": "2026-03-10",
			"customer": {"id": 99999},
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_quote)
		self.assertIsNone(fields["customer"])

	def test_from_pennylane_defaults_currency_to_eur(self):
		pl_quote = {
			"id": 504,
			"date": "2026-02-10",
			"deadline": "2026-03-10",
			"customer": None,
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_quote)
		self.assertEqual(fields["currency"], "EUR")

	def test_from_pennylane_deadline(self):
		pl_quote = {
			"id": 505,
			"date": "2026-02-10",
			"deadline": "2026-03-10",
			"customer": None,
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_quote)
		self.assertEqual(fields["deadline"], "2026-03-10")

	def test_from_pennylane_with_lines(self):
		pl_quote = {
			"id": 506,
			"date": "2026-02-10",
			"deadline": "2026-03-10",
			"customer": None,
			"invoice_lines": [
				{
					"label": "Design",
					"quantity": "4",
					"raw_currency_unit_price": "50.00",
					"currency_amount": "200.00",
				},
			],
		}
		fields = from_pennylane(pl_quote)
		self.assertEqual(len(fields["invoice_lines"]), 1)
		self.assertEqual(fields["invoice_lines"][0]["label"], "Design")
		self.assertAlmostEqual(fields["invoice_lines"][0]["unit_price"], 50.0)

	def test_locked_statuses(self):
		for status in ("accepted", "denied", "invoiced", "expired"):
			pl_quote = {
				"id": 600, "date": "2026-01-01", "deadline": "2026-02-01",
				"status": status, "customer": None, "invoice_lines": [],
			}
			self.assertTrue(from_pennylane(pl_quote)["_locked"], f"{status} should be locked")
