"""
Called after `bench install-app pennylane`.
"""

import frappe


def after_install():
	frappe.db.commit()
	print("Pennylane: app installed successfully.")
