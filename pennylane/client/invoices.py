"""Customer Invoice API calls."""

from .base import PennylaneClient


def get_invoice(client: PennylaneClient, pennylane_id: int) -> dict:
	return client.get(f"/customer_invoices/{pennylane_id}")


def create_invoice(client: PennylaneClient, payload: dict) -> dict:
	return client.post("/customer_invoices", data=payload)


def update_invoice(client: PennylaneClient, pennylane_id: int, payload: dict) -> dict:
	return client.put(f"/customer_invoices/{pennylane_id}", data=payload)


def list_invoices(client: PennylaneClient, **params):
	yield from client.paginate("/customer_invoices", params=params)


def get_changelog(client: PennylaneClient, cursor: str | None = None) -> dict:
	params = {"limit": 1000}
	if cursor:
		params["cursor"] = cursor
	return client.get("/changelogs/customer_invoices", params=params)
