"""
Map between Pennylane Customer doctype and Pennylane API payload.
"""

import frappe



def to_pennylane(doc_name: str) -> dict:
	"""Build a Pennylane create/update payload from a Pennylane Customer doc."""
	doc = frappe.get_doc("Pennylane Customer", doc_name)
	is_individual = doc.customer_type == "individual"

	payload: dict = {}

	if is_individual:
		payload["first_name"] = doc.first_name or ""
		payload["last_name"] = doc.last_name or ""
	else:
		payload["name"] = doc.customer_name

	# Shared optional fields
	if doc.email:
		payload["emails"] = [doc.email]
	if doc.phone:
		payload["phone"] = doc.phone
	if doc.recipient:
		payload["recipient"] = doc.recipient
	if doc.billing_language:
		pl_lang = _language_to_pennylane(doc.billing_language)
		if pl_lang:
			payload["billing_language"] = pl_lang
	if doc.reference:
		payload["reference"] = doc.reference
	if doc.notes:
		payload["notes"] = doc.notes
	if doc.billing_iban:
		payload["billing_iban"] = doc.billing_iban
	if doc.payment_conditions:
		payload["payment_conditions"] = doc.payment_conditions
	if doc.external_reference:
		payload["external_reference"] = doc.external_reference

	# Company-only tax fields
	if not is_individual:
		if doc.vat_number:
			payload["vat_number"] = doc.vat_number
		if doc.reg_no:
			payload["reg_no"] = doc.reg_no

	# Ledger account override
	if doc.ledger_account_number:
		payload["ledger_account"] = {"number": doc.ledger_account_number}

	# Billing address — always required by the API (both POST and PUT)
	payload["billing_address"] = {
		"address": doc.address_line1 or "",
		"postal_code": doc.postal_code or "",
		"city": doc.city or "",
		"country_alpha2": _country_to_alpha2(doc.country),
	}

	# Delivery address — only sent when at least one field is filled
	delivery = (doc.delivery_address_line1, doc.delivery_postal_code, doc.delivery_city, doc.delivery_country)
	if any(delivery):
		payload["delivery_address"] = {
			"address": doc.delivery_address_line1 or "",
			"postal_code": doc.delivery_postal_code or "",
			"city": doc.delivery_city or "",
			"country_alpha2": _country_to_alpha2(doc.delivery_country),
		}

	return payload


def from_pennylane(pl_customer: dict) -> dict:
	"""Extract fields for a Pennylane Customer doc from a Pennylane API object."""
	is_individual = pl_customer.get("customer_type") == "individual"
	billing = pl_customer.get("billing_address") or {}
	delivery = pl_customer.get("delivery_address") or {}
	emails = pl_customer.get("emails") or []
	ledger = pl_customer.get("ledger_account") or {}

	if is_individual:
		first = pl_customer.get("first_name", "")
		last = pl_customer.get("last_name", "")
		name = pl_customer.get("name") or f"{first} {last}".strip()
	else:
		name = pl_customer.get("name", "")

	fields = {
		"customer_name": name,
		"customer_type": pl_customer.get("customer_type", "company"),
		"pennylane_id": pl_customer.get("id"),
		"first_name": pl_customer.get("first_name"),
		"last_name": pl_customer.get("last_name"),
		"email": emails[0] if emails else None,
		"phone": pl_customer.get("phone"),
		"recipient": pl_customer.get("recipient"),
		"billing_language": _pennylane_to_language(pl_customer.get("billing_language")),
		"reference": pl_customer.get("reference"),
		"notes": pl_customer.get("notes"),
		"billing_iban": pl_customer.get("billing_iban"),
		"payment_conditions": pl_customer.get("payment_conditions"),
		"external_reference": pl_customer.get("external_reference"),
		"vat_number": pl_customer.get("vat_number"),
		"reg_no": pl_customer.get("reg_no"),
		"ledger_account_number": ledger.get("number"),
		# Billing address
		"address_line1": billing.get("address"),
		"postal_code": billing.get("postal_code"),
		"city": billing.get("city"),
		"country": _alpha2_to_country(billing.get("country_alpha2")),
		# Delivery address
		"delivery_address_line1": delivery.get("address"),
		"delivery_postal_code": delivery.get("postal_code"),
		"delivery_city": delivery.get("city"),
		"delivery_country": _alpha2_to_country(delivery.get("country_alpha2")),
	}

	return {k: v for k, v in fields.items() if v is not None}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


_LANGUAGE_TO_PENNYLANE = {
	"fr": "fr_FR",
	"en": "en_GB",
	"de": "de_DE",
}


def _language_to_pennylane(frappe_lang: str | None) -> str | None:
	"""Convert a Frappe Language code (e.g. 'fr') to a Pennylane billing_language value (e.g. 'fr_FR')."""
	if not frappe_lang:
		return None
	return _LANGUAGE_TO_PENNYLANE.get(frappe_lang.lower())


def _pennylane_to_language(pl_lang: str | None) -> str | None:
	"""Convert a Pennylane billing_language (e.g. 'fr_FR') to a Frappe Language code (e.g. 'fr')."""
	if not pl_lang:
		return None
	code = pl_lang.split("_")[0].lower()
	return frappe.db.get_value("Language", {"language_code": code}, "name")


def _country_to_alpha2(country_name: str | None) -> str:
	if not country_name:
		return "FR"
	code = frappe.db.get_value("Country", country_name, "code")
	return (code or "FR").upper()


def _alpha2_to_country(alpha2: str | None) -> str | None:
	if not alpha2:
		return None
	return frappe.db.get_value("Country", {"code": alpha2.lower()}, "name")
