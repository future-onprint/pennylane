"""PDF attachment utilities for Pennylane sync."""

import frappe


def attach_pdf(doc, public_file_url: str, filename: str) -> None:
	"""Download a PDF from *public_file_url* and attach it to *doc*.

	Replaces any existing File attachment whose ``file_name`` matches
	*filename* so that repeated syncs don't create duplicate attachments.

	Args:
		doc: A Frappe Document instance (already saved).
		public_file_url: The time-limited public URL returned by Pennylane.
		filename: The desired attachment filename (e.g. ``"invoice_123.pdf"``).
	"""
	import requests

	# 1. Delete existing attachments with the same filename
	existing_files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"file_name": filename,
		},
		pluck="name",
	)
	for file_name in existing_files:
		frappe.delete_doc("File", file_name, ignore_permissions=True, force=True)

	# 2. Download the PDF bytes
	response = requests.get(public_file_url, timeout=30)
	response.raise_for_status()
	pdf_bytes = response.content

	# 3. Create a new File doc attached to this doc
	file_doc = frappe.new_doc("File")
	file_doc.file_name = filename
	file_doc.attached_to_doctype = doc.doctype
	file_doc.attached_to_name = doc.name
	file_doc.is_private = 1
	file_doc.content = pdf_bytes
	file_doc.decode = False
	file_doc.insert(ignore_permissions=True)
