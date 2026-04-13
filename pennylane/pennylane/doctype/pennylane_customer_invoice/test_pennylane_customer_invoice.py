# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from pennylane.mappers.invoice import from_pennylane, to_pennylane

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


def make_customer(**kwargs) -> "frappe.Document":
	defaults = {"customer_name": "_Test Invoice Customer", "customer_type": "company"}
	defaults.update(kwargs)
	doc = frappe.new_doc("Pennylane Customer")
	doc.update(defaults)
	doc.insert(ignore_permissions=True)
	return doc


def make_invoice(customer_name: str, **kwargs) -> "frappe.Document":
	defaults = {
		"customer": customer_name,
		"date": "2026-01-15",
		"deadline": "2026-02-15",
		"invoice_lines": [
			{"label": "_Test Service", "quantity": 1.0, "unit_price": 100.0},
		],
	}
	defaults.update(kwargs)
	doc = frappe.new_doc("Pennylane Customer Invoice")
	doc.update(defaults)
	doc.insert(ignore_permissions=True)
	return doc


class IntegrationTestPennylaneCustomerInvoice(IntegrationTestCase):
	def setUp(self):
		self.customer = make_customer()

	def tearDown(self):
		frappe.db.delete("Pennylane Customer Invoice", {"customer": ["like", "_Test%"]})
		frappe.db.delete("Pennylane Customer", {"customer_name": ["like", "_Test%"]})
		frappe.db.commit()

	# ------------------------------------------------------------------
	# DocType
	# ------------------------------------------------------------------

	def test_create_minimal(self):
		invoice = make_invoice(self.customer.name)
		self.assertEqual(invoice.customer, self.customer.name)
		self.assertEqual(invoice.status, "draft")
		self.assertEqual(invoice.sync_status, "Pending")
		self.assertEqual(invoice.currency, "EUR")
		self.assertEqual(invoice.docstatus, 0)

	def test_create_with_lines(self):
		invoice = make_invoice(
			self.customer.name,
			invoice_lines=[
				{"label": "Line A", "quantity": 2.0, "unit_price": 50.0},
				{"label": "Line B", "quantity": 1.0, "unit_price": 200.0},
			],
		)
		self.assertEqual(len(invoice.invoice_lines), 2)
		self.assertEqual(invoice.invoice_lines[0].label, "Line A")

	def test_create_with_optional_fields(self):
		invoice = make_invoice(
			self.customer.name,
			external_reference="EXT-INV-001",
			language="fr_FR",
			pdf_invoice_subject="Facture de services",
		)
		self.assertEqual(invoice.external_reference, "EXT-INV-001")
		self.assertEqual(invoice.language, "fr_FR")
		self.assertEqual(invoice.pdf_invoice_subject, "Facture de services")

	# ------------------------------------------------------------------
	# Mapper — to_pennylane (draft)
	# ------------------------------------------------------------------

	def test_to_pennylane_draft(self):
		self.customer.pennylane_id = 42
		self.customer.save(ignore_permissions=True)

		invoice = make_invoice(self.customer.name)
		payload = to_pennylane(invoice.name)

		self.assertEqual(payload["date"], "2026-01-15")
		self.assertEqual(payload["deadline"], "2026-02-15")
		self.assertEqual(payload["customer_id"], 42)
		self.assertTrue(payload["draft"])
		self.assertIn("invoice_lines", payload)

	def test_to_pennylane_finalized(self):
		self.customer.pennylane_id = 43
		self.customer.save(ignore_permissions=True)

		invoice = make_invoice(self.customer.name)
		payload = to_pennylane(invoice.name, finalized=True)

		self.assertNotIn("draft", payload)

	def test_to_pennylane_includes_optional_fields(self):
		self.customer.pennylane_id = 44
		self.customer.save(ignore_permissions=True)

		invoice = make_invoice(
			self.customer.name,
			currency="USD",
			language="en_GB",
			external_reference="REF-X",
			pdf_invoice_subject="Invoice",
			special_mention="VAT exempt",
		)
		payload = to_pennylane(invoice.name)
		self.assertEqual(payload["currency"], "USD")
		self.assertEqual(payload["language"], "en_GB")
		self.assertEqual(payload["external_reference"], "REF-X")
		self.assertEqual(payload["pdf_invoice_subject"], "Invoice")
		self.assertEqual(payload["special_mention"], "VAT exempt")

	def test_to_pennylane_omits_missing_optional(self):
		self.customer.pennylane_id = 45
		self.customer.save(ignore_permissions=True)

		invoice = make_invoice(self.customer.name)
		payload = to_pennylane(invoice.name)
		self.assertNotIn("external_reference", payload)
		self.assertNotIn("language", payload)

	# ------------------------------------------------------------------
	# Mapper — from_pennylane
	# ------------------------------------------------------------------

	def test_from_pennylane_resolves_customer(self):
		self.customer.pennylane_id = 100
		self.customer.save(ignore_permissions=True)

		pl_invoice = {
			"id": 999,
			"date": "2026-01-20",
			"deadline": "2026-02-20",
			"status": "outstanding",
			"currency": "EUR",
			"draft": False,
			"customer": {"id": 100},
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_invoice)
		self.assertEqual(fields["pennylane_id"], 999)
		self.assertEqual(fields["customer"], self.customer.name)
		self.assertEqual(fields["status"], "outstanding")
		self.assertFalse(fields["_draft"])

	def test_from_pennylane_unknown_customer_is_none(self):
		pl_invoice = {
			"id": 888,
			"date": "2026-01-20",
			"deadline": "2026-02-20",
			"customer": {"id": 99999},
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_invoice)
		self.assertIsNone(fields["customer"])

	def test_from_pennylane_resolves_source_quote(self):
		# Create a quote with a known pennylane_id
		quote = frappe.new_doc("Pennylane Customer Quote")
		quote.customer = self.customer.name
		quote.date = "2026-01-01"
		quote.deadline = "2026-01-31"
		quote.pennylane_id = 77
		quote.invoice_lines = [{"label": "_Test", "quantity": 1.0, "unit_price": 10.0}]
		quote.insert(ignore_permissions=True)

		pl_invoice = {
			"id": 700,
			"date": "2026-01-20",
			"deadline": "2026-02-20",
			"customer": None,
			"quote": {"id": 77},
			"invoice_lines": [],
		}
		fields = from_pennylane(pl_invoice)
		self.assertEqual(fields["source_quote"], quote.name)

		frappe.delete_doc("Pennylane Customer Quote", quote.name, ignore_permissions=True)

	def test_from_pennylane_with_lines(self):
		pl_invoice = {
			"id": 777,
			"date": "2026-01-20",
			"deadline": "2026-02-20",
			"customer": None,
			"invoice_lines": [
				{
					"label": "Consulting",
					"quantity": "3",
					"raw_currency_unit_price": "100.00",
					"currency_amount": "300.00",
				},
			],
		}
		fields = from_pennylane(pl_invoice)
		self.assertEqual(len(fields["invoice_lines"]), 1)
		self.assertEqual(fields["invoice_lines"][0]["label"], "Consulting")
		self.assertAlmostEqual(fields["invoice_lines"][0]["unit_price"], 100.0)
