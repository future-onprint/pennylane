"""
Called before `bench remove-app pennylane`.
"""

import frappe


def before_uninstall():
	"""Deregister Pennylane webhook, then remove UI artifacts."""
	_deregister_webhook()

	if frappe.db.exists("Workspace Sidebar", "Pennylane"):
		frappe.delete_doc("Workspace Sidebar", "Pennylane", ignore_permissions=True, force=True)
		print("Pennylane: workspace sidebar removed.")

	if frappe.db.exists("Desktop Icon", "Pennylane"):
		frappe.delete_doc("Desktop Icon", "Pennylane", ignore_permissions=True, force=True)
		print("Pennylane: desktop icon removed.")

	frappe.db.commit()


def _deregister_webhook():
	"""Delete the Pennylane webhook subscription if one is registered."""
	try:
		subscription_id = frappe.db.get_single_value(
			"Pennylane Settings", "webhook_subscription_id"
		)
		if not subscription_id:
			return

		from pennylane.client.base import PennylaneClient
		from pennylane.client.webhooks import delete_subscription

		client = PennylaneClient.from_settings()
		delete_subscription(client)
		print("Pennylane: webhook subscription deregistered.")
	except Exception as exc:
		# Non-fatal — log and continue so uninstall is never blocked.
		print(f"Pennylane: webhook deregistration failed (continuing): {exc}")
