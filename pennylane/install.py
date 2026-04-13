"""
Called after `bench install-app pennylane`.
"""

import secrets

import frappe

# ---------------------------------------------------------------------------
# VAT Rates — all codes available in the Pennylane API.
# Encoding convention: numeric suffix = rate × 10
#   FR_200 → 20.0%  |  FR_55 → 5.5%  |  FR_21 → 2.1%
# Special format for sub-unit decimals:
#   FR_1_05 → 1.05%  |  FR_15_385 → 15.385%
# ---------------------------------------------------------------------------

_COUNTRY_NAMES: dict[str, str] = {
	"AD": "Andorre",
	"AT": "Autriche",
	"BE": "Belgique",
	"BG": "Bulgarie",
	"CH": "Suisse",
	"CY": "Chypre",
	"CZ": "Rép. tchèque",
	"DE": "Allemagne",
	"DK": "Danemark",
	"EE": "Estonie",
	"ES": "Espagne",
	"FI": "Finlande",
	"FR": "France",
	"GB": "Royaume-Uni",
	"GR": "Grèce",
	"HR": "Croatie",
	"HU": "Hongrie",
	"IE": "Irlande",
	"IT": "Italie",
	"LO": "LO",
	"LT": "Lituanie",
	"LU": "Luxembourg",
	"LV": "Lettonie",
	"MC": "Monaco",
	"MT": "Malte",
	"MU": "Île Maurice",
	"NL": "Pays-Bas",
	"NO": "Norvège",
	"PL": "Pologne",
	"PT": "Portugal",
	"RO": "Roumanie",
	"SE": "Suède",
	"SI": "Slovénie",
	"SK": "Slovaquie",
}

# All rate codes exposed by the Pennylane API.
_VAT_RATE_CODES: list[str] = [
	# France
	"FR_1_05", "FR_1_75", "FR_09", "FR_21", "FR_40", "FR_50", "FR_55",
	"FR_60", "FR_85", "FR_92", "FR_100", "FR_130", "FR_15_385",
	"FR_160", "FR_190", "FR_200",
	# France — construction (taux réduits pour travaux)
	"FR_85_construction", "FR_100_construction", "FR_200_construction",
	# Andorra
	"AD_10", "AD_45", "AD_95",
	# Austria
	"AT_100", "AT_130", "AT_190", "AT_200",
	# Belgium
	"BE_06", "BE_12", "BE_21",
	# Bulgaria
	"BG_90", "BG_200",
	# Switzerland
	"CH_25", "CH_26", "CH_30", "CH_37", "CH_77", "CH_81",
	# Cyprus
	"CY_30", "CY_50", "CY_80", "CY_90", "CY_190",
	# Czech Republic
	"CZ_100", "CZ_120", "CZ_150", "CZ_210",
	# Germany
	"DE_70", "DE_190",
	# Denmark
	"DK_250",
	# Estonia
	"EE_90", "EE_200", "EE_220", "EE_240",
	# Spain
	"ES_40", "ES_70", "ES_100", "ES_210",
	# Finland
	"FI_100", "FI_135", "FI_140", "FI_240", "FI_255",
	# United Kingdom
	"GB_50", "GB_200",
	# Greece
	"GR_40", "GR_60", "GR_130", "GR_170", "GR_240",
	# Croatia
	"HR_50", "HR_130", "HR_250",
	# Hungary
	"HU_50", "HU_100", "HU_270",
	# Ireland
	"IE_48", "IE_90", "IE_135", "IE_210", "IE_230",
	# Italy
	"IT_40", "IT_50", "IT_100", "IT_220",
	# Lithuania
	"LT_50", "LT_90", "LT_120", "LT_210",
	# LO
	"LO_10",
	# Luxembourg
	"LU_70", "LU_80", "LU_120", "LU_130", "LU_140", "LU_160", "LU_170",
	# Latvia
	"LV_50", "LV_120", "LV_210",
	# Monaco
	"MC_21", "MC_55", "MC_85", "MC_100", "MC_200",
	# Malta
	"MT_50", "MT_70", "MT_120", "MT_150",
	# Mauritius
	"MU_150",
	# Netherlands
	"NL_90", "NL_210",
	# Poland
	"PL_50", "PL_80", "PL_230",
	# Portugal
	"PT_60", "PT_130", "PT_160", "PT_180", "PT_220", "PT_230",
	# Romania
	"RO_50", "RO_90", "RO_110", "RO_190", "RO_210",
	# Sweden
	"SE_60", "SE_120", "SE_250",
	# Slovenia
	"SI_50", "SI_95", "SI_220",
	# Slovakia
	"SK_50", "SK_100", "SK_230",
	# Norway
	"NO_120", "NO_150", "NO_250",
	# Special regimes
	"exempt",
	"extracom",
	"intracom_21", "intracom_55", "intracom_85", "intracom_100",
	"crossborder",
	"mixed",
]


def _parse_rate(code: str) -> float:
	"""
	Derive the numeric VAT rate (%) from a Pennylane code.

	Encoding: suffix = rate * 10  →  FR_200 = 20.0%, FR_55 = 5.5%
	Exception: dotted decimals encoded with underscores:
	  FR_1_05 = 1.05%,  FR_15_385 = 15.385%
	"""
	if code in ("exempt", "extracom", "crossborder", "mixed"):
		return 0.0
	if code.startswith("intracom_"):
		return 0.0
	if code.endswith("_construction"):
		return _parse_rate(code[: -len("_construction")])

	parts = code.split("_", 1)
	if len(parts) < 2:
		return 0.0

	numeric = parts[1]

	if "_" in numeric:
		# FR_1_05 → "1" + "05" → 1.05
		# FR_15_385 → "15" + "385" → 15.385
		left, right = numeric.split("_", 1)
		try:
			return float(f"{left}.{right}")
		except ValueError:
			return 0.0

	try:
		return round(int(numeric) / 10, 4)
	except ValueError:
		return 0.0


def _fmt_rate(rate: float) -> str:
	"""Format a rate for display: 20.0 → '20', 5.5 → '5,5', 2.1 → '2,1'."""
	if rate == int(rate):
		return str(int(rate))
	return f"{rate:g}".replace(".", ",")


def _build_entry(code: str) -> dict:
	"""Build a full VAT rate entry dict from a Pennylane code."""
	# --- Special regimes ---
	if code == "exempt":
		return {
			"code": code,
			"label": "Exonéré de TVA",
			"rate": 0.0,
			"is_exempt": 1,
			"description": "Opérations exonérées de TVA : franchise en base, associations, professions médicales, etc.",
		}
	if code == "extracom":
		return {
			"code": code,
			"label": "Extra-communautaire (0 %)",
			"rate": 0.0,
			"is_exempt": 1,
			"description": "Exportations hors Union Européenne. TVA non applicable.",
		}
	if code == "crossborder":
		return {
			"code": code,
			"label": "Transfrontalier (0 %)",
			"rate": 0.0,
			"is_exempt": 1,
			"description": "Opérations transfrontalières soumises à autoliquidation.",
		}
	if code == "mixed":
		return {
			"code": code,
			"label": "Taux mixte",
			"rate": 0.0,
			"is_exempt": 1,
			"description": "Opération à taux multiples.",
		}
	if code.startswith("intracom_"):
		suffix = code.split("_", 1)[1].replace("_", ".")
		return {
			"code": code,
			"label": f"Intracommunautaire ({suffix} %)",
			"rate": 0.0,
			"is_exempt": 1,
			"description": "Livraison intracommunautaire. TVA autoliquidée par l'acquéreur.",
		}

	# --- Construction rates ---
	if code.endswith("_construction"):
		rate = _parse_rate(code)
		return {
			"code": code,
			"label": f"TVA {_fmt_rate(rate)} % — France (Construction)",
			"rate": rate,
			"is_exempt": 0,
			"description": "Taux applicable aux travaux de rénovation et construction en France.",
		}

	# --- Standard country rate ---
	rate = _parse_rate(code)
	country_code = code.split("_")[0]
	country = _COUNTRY_NAMES.get(country_code, country_code)
	return {
		"code": code,
		"label": f"TVA {_fmt_rate(rate)} % — {country}",
		"rate": rate,
		"is_exempt": 0,
		"description": "",
	}


# ---------------------------------------------------------------------------
# Units — all units available in the Pennylane API.
# ---------------------------------------------------------------------------

_UNITS: list[dict] = [
	{"code": "piece",    "label": "Unité",         "symbol": "unité"},
	{"code": "hour",     "label": "Heure",          "symbol": "heure"},
	{"code": "day",      "label": "Jour",            "symbol": "jour"},
	{"code": "month",    "label": "Mois",            "symbol": "mois"},
	{"code": "kilogram", "label": "Kilogramme",      "symbol": "kg"},
	{"code": "m2",       "label": "Mètre carré",     "symbol": "m²"},
	{"code": "m3",       "label": "Mètre cube",      "symbol": "m³"},
	{"code": "ton",      "label": "Tonne",           "symbol": "tonne"},
	{"code": "mg",       "label": "Milligramme",     "symbol": "mg"},
	{"code": "percent",  "label": "Pourcentage",     "symbol": "%"},
	{"code": "no_unit",  "label": "Sans unité",      "symbol": "(pas d'unité)"},
]


# ---------------------------------------------------------------------------
# Install hooks
# ---------------------------------------------------------------------------

_WORKSPACE_SIDEBAR_ITEMS = [
	{
		"child": 0,
		"collapsible": 1,
		"icon": "home",
		"indent": 0,
		"keep_closed": 0,
		"label": "Dashboard",
		"link_to": "Pennylane",
		"link_type": "Workspace",
		"show_arrow": 0,
		"type": "Link",
	},
	{
		"child": 0,
		"collapsible": 1,
		"icon": "",
		"indent": 0,
		"keep_closed": 0,
		"label": "Sales",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Section Break",
	},
	{
		"child": 1,
		"collapsible": 1,
		"icon": "money-coins-1",
		"indent": 0,
		"keep_closed": 0,
		"label": "Invoices",
		"link_to": "Pennylane Customer Invoice",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Link",
	},
	{
		"child": 1,
		"collapsible": 1,
		"icon": "notebook-pen",
		"indent": 0,
		"keep_closed": 0,
		"label": "Quotes",
		"link_to": "Pennylane Customer Quote",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Link",
	},
	{
		"child": 1,
		"collapsible": 1,
		"icon": "stock",
		"indent": 0,
		"keep_closed": 0,
		"label": "Products",
		"link_to": "Pennylane Product",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Link",
	},
	{
		"child": 1,
		"collapsible": 1,
		"icon": "users",
		"indent": 0,
		"keep_closed": 0,
		"label": "Customers",
		"link_to": "Pennylane Customer",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Link",
	},
	{
		"child": 0,
		"collapsible": 1,
		"indent": 0,
		"keep_closed": 1,
		"label": "Advanced",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Section Break",
	},
	{
		"child": 1,
		"collapsible": 1,
		"icon": "cog",
		"indent": 0,
		"keep_closed": 0,
		"label": "Settings",
		"link_to": "Pennylane Settings",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Link",
	},
	{
		"child": 1,
		"collapsible": 1,
		"icon": "clock-fading",
		"indent": 0,
		"keep_closed": 0,
		"label": "Sync Queue",
		"link_to": "Pennylane Sync Queue",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Link",
	},
	{
		"child": 1,
		"collapsible": 1,
		"icon": "logs",
		"indent": 0,
		"keep_closed": 0,
		"label": "Sync Logs",
		"link_to": "Pennylane Sync Log",
		"link_type": "DocType",
		"show_arrow": 0,
		"type": "Link",
	},
]


def before_install():
	"""Remove stale Workspace Sidebar and Desktop Icon left over from a previous installation."""
	if frappe.db.exists("Workspace Sidebar", "Pennylane"):
		frappe.delete_doc("Workspace Sidebar", "Pennylane", ignore_permissions=True, force=True)
	if frappe.db.exists("Desktop Icon", "Pennylane"):
		frappe.delete_doc("Desktop Icon", "Pennylane", ignore_permissions=True, force=True)


def after_install():
	_ensure_pennylane_manager_role()
	_seed_vat_rates()
	_seed_units()
	_ensure_webhook_secret()
	_setup_workspace_sidebar()
	frappe.db.commit()
	print("Pennylane: app installed successfully.")


def after_migrate():
	_setup_workspace_sidebar()
	frappe.db.commit()
	print("Pennylane: workspace sidebar synced.")


def _ensure_pennylane_manager_role():
	"""Create the Pennylane Manager role if it does not already exist."""
	if frappe.db.exists("Role", "Pennylane Manager"):
		return
	frappe.get_doc({
		"doctype": "Role",
		"role_name": "Pennylane Manager",
		"desk_access": 1,
	}).insert(ignore_permissions=True)
	print("Pennylane: created role 'Pennylane Manager'.")


def _seed_vat_rates():
	"""Insert Pennylane VAT rates if they don't already exist. Safe to re-run."""
	created = 0
	for code in _VAT_RATE_CODES:
		if frappe.db.exists("Pennylane VAT Rate", code):
			continue
		entry = _build_entry(code)
		frappe.get_doc({"doctype": "Pennylane VAT Rate", **entry}).insert(ignore_permissions=True)
		created += 1
	print(f"Pennylane: seeded {created} VAT rate(s) ({len(_VAT_RATE_CODES)} total).")


def _seed_units():
	"""Insert Pennylane units if they don't already exist. Safe to re-run."""
	created = 0
	for unit in _UNITS:
		if frappe.db.exists("Pennylane Unit", unit["code"]):
			continue
		frappe.get_doc({"doctype": "Pennylane Unit", **unit}).insert(ignore_permissions=True)
		created += 1
	print(f"Pennylane: seeded {created} unit(s) ({len(_UNITS)} total).")


def _ensure_webhook_secret():
	"""Generate a webhook secret automatically if not already configured."""
	settings = frappe.get_single("Pennylane Settings")
	if not settings.webhook_secret:
		settings.webhook_secret = secrets.token_hex(32)
		settings.save(ignore_permissions=True)


def _setup_workspace_sidebar():
	"""Create or overwrite the Pennylane Workspace Sidebar."""
	if frappe.db.exists("Workspace Sidebar", "Pennylane"):
		doc = frappe.get_doc("Workspace Sidebar", "Pennylane")
		doc.items = []
	else:
		doc = frappe.new_doc("Workspace Sidebar")
		doc.name = "Pennylane"
		doc.title = "Pennylane"
		doc.app = "pennylane"
		doc.module = "Pennylane"
		doc.standard = 0

	for item in _WORKSPACE_SIDEBAR_ITEMS:
		doc.append("items", item)

	doc.save(ignore_permissions=True)
	print("Pennylane: workspace sidebar configured.")


