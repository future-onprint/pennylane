"""Quote API calls."""

from .base import PennylaneClient


def get_quote(client: PennylaneClient, pennylane_id: int) -> dict:
	return client.get(f"/quotes/{pennylane_id}")


def create_quote(client: PennylaneClient, payload: dict) -> dict:
	return client.post("/quotes", data=payload)


def update_quote(client: PennylaneClient, pennylane_id: int, payload: dict) -> dict:
	return client.put(f"/quotes/{pennylane_id}", data=payload)


def list_quotes(client: PennylaneClient, **params):
	yield from client.paginate("/quotes", params=params)


def get_changelog(client: PennylaneClient, cursor: str | None = None) -> dict:
	params = {"limit": 1000}
	if cursor:
		params["cursor"] = cursor
	return client.get("/changelogs/quotes", params=params)
