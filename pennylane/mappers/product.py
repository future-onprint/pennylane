"""Map between Pennylane Product doctype and Pennylane API payload."""

import frappe


def to_pennylane(doc_name: str) -> dict:
	doc = frappe.get_doc("Pennylane Product", doc_name)
	payload = {"label": doc.label}

	if doc.reference:
		payload["reference"] = doc.reference
	if doc.external_reference:
		payload["external_reference"] = doc.external_reference
	if doc.unit:
		payload["unit"] = frappe.db.get_value("Pennylane Unit", doc.unit, "code") or doc.unit
	if doc.vat_rate:
		payload["vat_rate"] = doc.vat_rate
	if doc.currency_amount is not None:
		payload["price_before_tax"] = str(doc.currency_amount)
	if doc.currency:
		payload["currency"] = doc.currency
	if doc.description:
		payload["description"] = doc.description

	return payload


def from_pennylane(pl_product: dict) -> dict:
	return {
		"label": pl_product.get("label", ""),
		"pennylane_id": pl_product.get("id"),
		"reference": pl_product.get("reference"),
		"external_reference": pl_product.get("external_reference"),
		"unit": frappe.db.get_value("Pennylane Unit", {"code": pl_product.get("unit")}, "name"),
		"vat_rate": pl_product.get("vat_rate"),
		"currency_amount": pl_product.get("price_before_tax"),
		"currency": pl_product.get("currency"),
		"price": pl_product.get("price"),
		"description": pl_product.get("description"),
	}
