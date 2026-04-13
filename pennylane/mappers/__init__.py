from datetime import datetime, timezone


def parse_pennylane_dt(value: str | None) -> str | None:
	"""Convert a Pennylane ISO 8601 timestamp to a MySQL-compatible datetime string.

	Pennylane returns e.g. '2024-01-25T11:14:31.399852Z'.
	MySQL Datetime expects 'YYYY-MM-DD HH:MM:SS'.
	"""
	if not value:
		return None
	try:
		dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
		return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
	except Exception:
		return None
