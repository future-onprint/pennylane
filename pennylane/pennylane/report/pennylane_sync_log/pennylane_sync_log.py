# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

"""Pennylane Sync Log — Script Report."""

import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "creation",
			"fieldtype": "Datetime",
			"label": "Date / Time",
			"width": 160,
		},
		{
			"fieldname": "direction",
			"fieldtype": "Data",
			"label": "Direction",
			"width": 80,
		},
		{
			"fieldname": "resource_type",
			"fieldtype": "Data",
			"label": "Resource Type",
			"width": 130,
		},
		{
			"fieldname": "operation",
			"fieldtype": "Data",
			"label": "Operation",
			"width": 90,
		},
		{
			"fieldname": "status",
			"fieldtype": "Data",
			"label": "Status",
			"width": 90,
		},
		{
			"fieldname": "frappe_doctype",
			"fieldtype": "Data",
			"label": "Frappe DocType",
			"width": 180,
		},
		{
			"fieldname": "frappe_docname",
			"fieldtype": "Data",
			"label": "Frappe Document",
			"width": 180,
		},
		{
			"fieldname": "pennylane_id",
			"fieldtype": "Data",
			"label": "Pennylane ID",
			"width": 110,
		},
		{
			"fieldname": "error_message",
			"fieldtype": "Data",
			"label": "Error Message",
			"width": 300,
		},
	]


def get_data(filters: dict) -> list:
	conditions = _build_conditions(filters)

	return frappe.db.sql(
		f"""
		SELECT
			creation,
			direction,
			resource_type,
			operation,
			status,
			frappe_doctype,
			frappe_docname,
			pennylane_id,
			error_message
		FROM `tabPennylane Sync Log`
		WHERE 1=1
		{conditions["where"]}
		ORDER BY creation DESC
		LIMIT 5000
		""",
		conditions["values"],
		as_dict=True,
	)


def _build_conditions(filters: dict) -> dict:
	"""Build SQL WHERE clauses and value tuple from filters dict."""
	where_parts = []
	values = []

	status = filters.get("status")
	if status and status != "All":
		where_parts.append("AND status = %s")
		values.append(status)

	direction = filters.get("direction")
	if direction:
		where_parts.append("AND direction = %s")
		values.append(direction)

	resource_type = filters.get("resource_type")
	if resource_type:
		where_parts.append("AND resource_type = %s")
		values.append(resource_type)

	date_from = filters.get("date_from")
	if date_from:
		where_parts.append("AND DATE(creation) >= %s")
		values.append(date_from)

	date_to = filters.get("date_to")
	if date_to:
		where_parts.append("AND DATE(creation) <= %s")
		values.append(date_to)

	return {
		"where": " ".join(where_parts),
		"values": tuple(values),
	}
