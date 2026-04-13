"""
Pennylane webhook subscription API client.

One subscription per API token. Endpoints:
  GET    /webhook_subscription          → current subscription (no secret)
  POST   /webhook_subscription          → create (returns secret once)
  PUT    /webhook_subscription          → update events / enabled flag
  DELETE /webhook_subscription          → remove subscription
"""

from __future__ import annotations

from pennylane.client.base import PennylaneClient
from pennylane.client.exceptions import PennylaneNotFoundError

_PATH = "/webhook_subscription"

# All event types supported by the Pennylane API.
ALL_EVENTS = [
    "customer_invoice.created",
    "quote.created",
    "dms_file.created",
]


def get_subscription(client: PennylaneClient) -> dict | None:
    """Return the current webhook subscription, or None if none exists."""
    try:
        return client.get(_PATH)
    except PennylaneNotFoundError:
        return None


def create_subscription(
    client: PennylaneClient,
    callback_url: str,
    events: list[str],
) -> dict:
    """
    Create a webhook subscription.

    Returns the full response including the ``secret`` field.
    The secret is only returned once — store it immediately.
    """
    return client.post(_PATH, data={"callback_url": callback_url, "events": events})


def update_subscription(
    client: PennylaneClient,
    events: list[str],
    enabled: bool = True,
) -> dict:
    """Update the events list and/or enabled state of the existing subscription."""
    return client.put(_PATH, data={"events": events, "enabled": enabled})


def delete_subscription(client: PennylaneClient) -> None:
    """Delete the webhook subscription. Silently ignores 404."""
    try:
        client.delete(_PATH)
    except PennylaneNotFoundError:
        pass
