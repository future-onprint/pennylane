"""Product API calls."""

from .base import PennylaneClient


def get_product(client: PennylaneClient, pennylane_id: int) -> dict:
	return client.get(f"/products/{pennylane_id}")


def create_product(client: PennylaneClient, payload: dict) -> dict:
	return client.post("/products", data=payload)


def update_product(client: PennylaneClient, pennylane_id: int, payload: dict) -> dict:
	return client.put(f"/products/{pennylane_id}", data=payload)


def list_products(client: PennylaneClient, **params):
	yield from client.paginate("/products", params=params)


def get_changelog(client: PennylaneClient, cursor: str | None = None, start_date: str | None = None) -> dict:
	params = {"limit": 1000}
	if cursor:
		params["cursor"] = cursor
	elif start_date:
		params["start_date"] = start_date
	return client.get("/changelogs/products", params=params)
