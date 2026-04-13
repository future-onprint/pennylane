"""Customer Invoice API calls."""

from .base import PennylaneClient


def get_invoice(client: PennylaneClient, pennylane_id: int) -> dict:
	return client.get(f"/customer_invoices/{pennylane_id}")


def create_invoice(client: PennylaneClient, payload: dict) -> dict:
	return client.post("/customer_invoices", data=payload)


def create_invoice_from_quote(client: PennylaneClient, payload: dict) -> dict:
	"""Create an invoice from an existing Pennylane quote (inherits customer and lines)."""
	return client.post("/customer_invoices/create_from_quote", data=payload)


def update_invoice(client: PennylaneClient, pennylane_id: int, payload: dict) -> dict:
	return client.put(f"/customer_invoices/{pennylane_id}", data=payload)


def list_invoices(client: PennylaneClient, **params):
	yield from client.paginate("/customer_invoices", params=params)


def get_invoice_lines(client: PennylaneClient, invoice_id: int) -> list:
	return list(client.paginate(f"/customer_invoices/{invoice_id}/invoice_lines"))


def get_changelog(client: PennylaneClient, cursor: str | None = None, start_date: str | None = None) -> dict:
	params = {"limit": 1000}
	if cursor:
		params["cursor"] = cursor
	elif start_date:
		params["start_date"] = start_date
	return client.get("/changelogs/customer_invoices", params=params)
