"""
Called before `bench remove-app pennylane`.
"""

import frappe


def before_uninstall():
	"""Remove the Pennylane Workspace Sidebar and Desktop Icon."""
	if frappe.db.exists("Workspace Sidebar", "Pennylane"):
		frappe.delete_doc("Workspace Sidebar", "Pennylane", ignore_permissions=True, force=True)
		print("Pennylane: workspace sidebar removed.")

	if frappe.db.exists("Desktop Icon", "Pennylane"):
		frappe.delete_doc("Desktop Icon", "Pennylane", ignore_permissions=True, force=True)
		print("Pennylane: desktop icon removed.")

	frappe.db.commit()
