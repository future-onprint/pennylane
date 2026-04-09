"""
Build Pennylane invoice_lines payload from Pennylane Invoice Line child rows.

A line can reference an existing Pennylane Product (product_id is sent)
or be a free-text line (no product_id: label, raw_currency_unit_price, unit,
vat_rate and quantity are all required).

Discount is an object {"type": "relative"|"absolute", "value": "<number>"}.
"""

import frappe


def lines_to_pennylane(doc_lines: list) -> list:
	"""Convert a list of Pennylane Invoice Line child docs to API payload."""
	result = []
	for line in doc_lines:
		item = {
			"quantity": line.quantity,
		}

		if line.vat_rate:
			item["vat_rate"] = line.vat_rate
		if line.unit:
			item["unit"] = frappe.db.get_value("Pennylane Unit", line.unit, "code") or line.unit
		if line.description:
			item["description"] = line.description
		if line.discount:
			item["discount"] = {
				"type": line.discount_type or "relative",
				"value": str(line.discount),
			}

		# Product-based line: only product_id + quantity required
		if line.product:
			pl_id = frappe.db.get_value("Pennylane Product", line.product, "pennylane_id")
			if pl_id:
				item["product_id"] = pl_id
				if line.label:
					item["label"] = line.label
				item["raw_currency_unit_price"] = str(line.unit_price)
				result.append(item)
				continue

		# Standard line: label, raw_currency_unit_price, unit, vat_rate all required
		item["label"] = line.label
		item["raw_currency_unit_price"] = str(line.unit_price)
		result.append(item)

	return result


def lines_from_pennylane(pl_lines: list, currency: str | None = None) -> list:
	"""Convert Pennylane API invoice_lines to child table rows."""
	rows = []
	for line in pl_lines:
		product_id = line.get("product_id") or (line.get("product") or {}).get("id")
		frappe_product = None
		if product_id:
			frappe_product = frappe.db.get_value(
				"Pennylane Product", {"pennylane_id": product_id}, "name"
			)

		# Parse discount object → type + value
		discount_obj = line.get("discount") or {}
		discount_type = discount_obj.get("type", "relative")
		discount_value = float(discount_obj.get("value") or 0)

		rows.append({
			"product": frappe_product,
			"label": line.get("label", ""),
			"quantity": float(line.get("quantity") or 1),
			"unit_price": float(line.get("raw_currency_unit_price") or 0),
			"vat_rate": line.get("vat_rate"),
			"unit": frappe.db.get_value("Pennylane Unit", {"code": line.get("unit")}, "name"),
			"description": line.get("description"),
			"discount_type": discount_type,
			"discount": discount_value,
			"currency_amount": float(line.get("currency_amount") or 0),
			"currency": currency,
		})
	return rows
