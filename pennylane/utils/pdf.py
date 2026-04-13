"""PDF attachment utilities for Pennylane sync."""

import frappe


def attach_pdf(doc, public_file_url: str, filename: str, replace: bool = False) -> None:
	"""Download a PDF from *public_file_url* and attach it to *doc*.

	Args:
		doc: A Frappe Document instance (already saved).
		public_file_url: The time-limited public URL returned by Pennylane.
		filename: The desired attachment filename (e.g. ``"invoice_123.pdf"``).
		replace: When False (default), skip if the file is already attached —
			safe for invoices whose PDF never changes. Set to True for quotes
			whose PDF is regenerated on every update.
	"""
	import requests

	existing = frappe.db.get_value("File", {
		"attached_to_doctype": doc.doctype,
		"attached_to_name": doc.name,
		"file_name": filename,
	}, "name")

	if existing:
		if not replace:
			return
		frappe.delete_doc("File", existing, ignore_permissions=True, force=True)

	response = requests.get(public_file_url, timeout=30)
	response.raise_for_status()

	file_doc = frappe.new_doc("File")
	file_doc.file_name = filename
	file_doc.attached_to_doctype = doc.doctype
	file_doc.attached_to_name = doc.name
	file_doc.is_private = 1
	file_doc.content = response.content
	file_doc.decode = False
	file_doc.insert(ignore_permissions=True)
