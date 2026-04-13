"""Map between Pennylane Customer Invoice doctype and Pennylane API payload."""

import frappe

from .invoice_line import lines_from_pennylane, lines_to_pennylane


def to_pennylane(doc_name: str, *, finalized: bool = False) -> dict:
	doc = frappe.get_doc("Pennylane Customer Invoice", doc_name)
	customer_pl_id = frappe.db.get_value("Pennylane Customer", doc.customer, "pennylane_id")

	payload = {
		"date": str(doc.date),
		"deadline": str(doc.deadline),
		"customer_id": customer_pl_id,
		"invoice_lines": lines_to_pennylane(doc.invoice_lines),
	}

	if not finalized:
		payload["draft"] = True

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


def from_pennylane(pl_invoice: dict) -> dict:
	pl_customer_id = (pl_invoice.get("customer") or {}).get("id")
	customer_name = None
	if pl_customer_id:
		customer_name = frappe.db.get_value(
			"Pennylane Customer", {"pennylane_id": pl_customer_id}, "name"
		)

	# Resolve source quote if the invoice was generated from one
	pl_quote_id = (pl_invoice.get("quote") or {}).get("id")
	source_quote = None
	if pl_quote_id:
		source_quote = frappe.db.get_value(
			"Pennylane Customer Quote", {"pennylane_id": pl_quote_id}, "name"
		)

	return {
		"customer": customer_name,
		"pennylane_id": pl_invoice.get("id"),
		"invoice_number": pl_invoice.get("invoice_number"),
		"date": pl_invoice.get("date"),
		"deadline": pl_invoice.get("deadline"),
		"label": pl_invoice.get("label"),
		"status": pl_invoice.get("status", "draft"),
		"currency": pl_invoice.get("currency", "EUR"),
		"language": pl_invoice.get("language"),
		"amount": pl_invoice.get("amount"),
		"currency_amount": pl_invoice.get("currency_amount"),
		"external_reference": pl_invoice.get("external_reference"),
		"pdf_invoice_subject": pl_invoice.get("pdf_invoice_subject"),
		"pdf_invoice_free_text": pl_invoice.get("pdf_invoice_free_text"),
		"pdf_description": pl_invoice.get("pdf_description"),
		"special_mention": pl_invoice.get("special_mention"),
		"source_quote": source_quote,
		"invoice_lines": lines_from_pennylane(pl_invoice.get("invoice_lines") or [], pl_invoice.get("currency")),
		# draft flag used by sync to decide whether to submit
		"_draft": pl_invoice.get("draft", True),
	}
