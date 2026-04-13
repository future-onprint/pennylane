"""Customer API calls."""

from .base import PennylaneClient


def get_customer(client: PennylaneClient, pennylane_id: int) -> dict:
	"""Fetch a customer by ID. Works for both company and individual customers."""
	return client.get(f"/customers/{pennylane_id}")


def get_company_customer(client: PennylaneClient, pennylane_id: int) -> dict:
	"""Fetch a company customer specifically (used for push operations)."""
	return client.get(f"/company_customers/{pennylane_id}")


def create_customer(client: PennylaneClient, payload: dict, customer_type: str = "company") -> dict:
	endpoint = "/individual_customers" if customer_type == "individual" else "/company_customers"
	return client.post(endpoint, data=payload)


def update_customer(client: PennylaneClient, pennylane_id: int, payload: dict, customer_type: str = "company") -> dict:
	endpoint = f"/individual_customers/{pennylane_id}" if customer_type == "individual" else f"/company_customers/{pennylane_id}"
	return client.put(endpoint, data=payload)


def list_customers(client: PennylaneClient, **params):
	"""Generator yielding all customers (company and individual)."""
	yield from client.paginate("/customers", params=params)


def get_customer_contacts(client: PennylaneClient, pl_customer_id: int) -> list:
	"""Fetch all contacts for a Pennylane customer. Returns a list of contact dicts."""
	return list(client.paginate(f"/customers/{pl_customer_id}/contacts"))


def get_changelog(client: PennylaneClient, start_date: str | None = None, cursor: str | None = None) -> dict:
	params = {"limit": 1000}
	if start_date:
		params["start_date"] = start_date
	if cursor:
		params["cursor"] = cursor
	return client.get("/changelogs/customers", params=params)
