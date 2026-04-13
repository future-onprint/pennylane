"""
Pennylane API HTTP client with Redis-backed rate limiting.

Rate limit: 25 requests per 5 seconds (shared across all workers).
"""

import json
import time

import frappe
import requests

from .exceptions import (
	PennylaneAuthError,
	PennylaneError,
	PennylaneNotFoundError,
	PennylanePermissionError,
	PennylaneRateLimitError,
	PennylaneServerError,
	PennylaneValidationError,
)

_RATE_LIMIT_KEY = "pennylane_rate_limit"
_RATE_LIMIT_MAX = 25
_RATE_LIMIT_WINDOW = 5  # seconds


class PennylaneClient:
	def __init__(self, api_token: str, base_url: str = "https://app.pennylane.com/api/external/v2"):
		self.api_token = api_token
		self.base_url = base_url.rstrip("/")
		self.session = requests.Session()
		self.session.headers.update(
			{
				"Authorization": f"Bearer {api_token}",
				"Accept": "application/json",
				"Content-Type": "application/json",
			}
		)

	@classmethod
	def from_settings(cls) -> "PennylaneClient":
		settings = frappe.get_cached_doc("Pennylane Settings")
		token = settings.get_password("api_token")
		if not token:
			raise PennylaneError("Pennylane API token is not configured.")
		return cls(api_token=token, base_url=settings.base_url)

	# ------------------------------------------------------------------
	# Rate limiting (Redis shared counter)
	# ------------------------------------------------------------------

	def _throttle(self):
		"""Block until we are within the 25 req/5s rate limit.

		Uses a fixed-window counter keyed by time bucket so the counter
		resets naturally without relying on Redis TTL expiry during retries
		(the previous approach reset the TTL on every retry, causing an
		infinite loop once the limit was reached).
		"""
		cache = frappe.cache()
		while True:
			bucket = int(time.time() // _RATE_LIMIT_WINDOW)
			key = f"{_RATE_LIMIT_KEY}:{bucket}"
			count = cache.incr(key)
			if count == 1:
				# First request in this window — set expiry so Redis cleans up
				cache.expire(key, _RATE_LIMIT_WINDOW * 2)
			if count <= _RATE_LIMIT_MAX:
				return
			# Over limit — sleep until the next window starts
			next_window = (bucket + 1) * _RATE_LIMIT_WINDOW
			wait = next_window - time.time()
			time.sleep(max(wait, 0.05))

	# ------------------------------------------------------------------
	# Core request
	# ------------------------------------------------------------------

	def _request(self, method: str, path: str, **kwargs) -> dict:
		self._throttle()
		url = f"{self.base_url}{path}"
		resp = self.session.request(method, url, **kwargs)
		return self._handle_response(resp)

	def _handle_response(self, resp: requests.Response) -> dict:
		if resp.status_code == 204:
			return {}

		try:
			data = resp.json()
		except Exception:
			data = {"raw": resp.text}

		if resp.ok:
			return data

		message = data.get("message") or data.get("error") or resp.text

		if resp.status_code == 401:
			raise PennylaneAuthError(message, status_code=401, response=data)
		if resp.status_code == 403:
			raise PennylanePermissionError(message, status_code=403, response=data)
		if resp.status_code == 404:
			raise PennylaneNotFoundError(message, status_code=404, response=data)
		if resp.status_code == 422:
			raise PennylaneValidationError(
				message, status_code=422, response=data, details=data.get("details", [])
			)
		if resp.status_code == 429:
			raise PennylaneRateLimitError(message, status_code=429, response=data)
		if resp.status_code >= 500:
			raise PennylaneServerError(message, status_code=resp.status_code, response=data)

		raise PennylaneError(message, status_code=resp.status_code, response=data)

	# ------------------------------------------------------------------
	# Convenience methods
	# ------------------------------------------------------------------

	def get(self, path: str, params: dict | None = None) -> dict:
		return self._request("GET", path, params=params)

	def post(self, path: str, data: dict | None = None) -> dict:
		return self._request("POST", path, json=data)

	def put(self, path: str, data: dict | None = None) -> dict:
		return self._request("PUT", path, json=data)

	def delete(self, path: str) -> dict:
		return self._request("DELETE", path)

	# ------------------------------------------------------------------
	# Pagination helper
	# ------------------------------------------------------------------

	def paginate(self, path: str, params: dict | None = None):
		"""Yield every item from a cursor-paginated list endpoint."""
		params = dict(params or {})
		params.setdefault("limit", 100)

		while True:
			resp = self.get(path, params=params)
			for item in resp.get("items", []):
				yield item
			if not resp.get("has_more"):
				break
			params["cursor"] = resp["next_cursor"]

	# ------------------------------------------------------------------
	# Filter helper
	# ------------------------------------------------------------------

	@staticmethod
	def build_filter(field: str, operator: str, value) -> str:
		"""Return a JSON filter string ready to pass as ?filter=..."""
		return json.dumps([{"field": field, "operator": operator, "value": value}])
