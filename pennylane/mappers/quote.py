"""Map between Pennylane Customer Quote doctype and Pennylane API payload."""

import frappe

from .invoice_line import lines_from_pennylane, lines_to_pennylane

# Statuses that mean the quote is no longer editable
_LOCKED_STATUSES = {"accepted", "denied", "invoiced", "expired"}


def to_pennylane(doc_name: str) -> dict:
	doc = frappe.get_doc("Pennylane Customer Quote", doc_name)
	customer_pl_id = frappe.db.get_value("Pennylane Customer", doc.customer, "pennylane_id")

	payload = {
		"date": str(doc.date),
		"deadline": str(doc.deadline),
		"customer_id": customer_pl_id,
		"invoice_lines": lines_to_pennylane(doc.invoice_lines),
	}

	if doc.label:
		payload["label"] = doc.label
	if doc.currency:
		payload["currency"] = doc.currency
	if doc.language:
		payload["language"] = doc.language
	if doc.external_reference:
		payload["external_reference"] = doc.external_reference
	if doc.pdf_invoice_subject:
		payload["pdf_invoice_subject"] = doc.pdf_invoice_subject
	if doc.pdf_invoice_free_text:
		payload["pdf_invoice_free_text"] = doc.pdf_invoice_free_text
	if doc.pdf_description:
		payload["pdf_description"] = doc.pdf_description
	if doc.special_mention:
		payload["special_mention"] = doc.special_mention

	return payload


def from_pennylane(pl_quote: dict) -> dict:
	pl_customer_id = (pl_quote.get("customer") or {}).get("id")
	customer_name = None
	if pl_customer_id:
		customer_name = frappe.db.get_value(
			"Pennylane Customer", {"pennylane_id": pl_customer_id}, "name"
		)

	status = pl_quote.get("status", "pending")

	return {
		"customer": customer_name,
		"pennylane_id": pl_quote.get("id"),
		"quote_number": pl_quote.get("quote_number"),
		"date": pl_quote.get("date"),
		"deadline": pl_quote.get("deadline"),
		"label": pl_quote.get("label"),
		"status": status,
		"currency": pl_quote.get("currency", "EUR"),
		"language": pl_quote.get("language"),
		"amount": pl_quote.get("amount"),
		"currency_amount": pl_quote.get("currency_amount"),
		"external_reference": pl_quote.get("external_reference"),
		"pdf_invoice_subject": pl_quote.get("pdf_invoice_subject"),
		"pdf_invoice_free_text": pl_quote.get("pdf_invoice_free_text"),
		"pdf_description": pl_quote.get("pdf_description"),
		"special_mention": pl_quote.get("special_mention"),
		"invoice_lines": lines_from_pennylane(pl_quote.get("invoice_lines") or []),
		# Used by sync to decide whether to submit the Frappe doc
		"_locked": status in _LOCKED_STATUSES,
	}
