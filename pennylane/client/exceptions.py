class PennylaneError(Exception):
	"""Base exception for all Pennylane API errors."""

	def __init__(self, message, status_code=None, response=None):
		super().__init__(message)
		self.status_code = status_code
		self.response = response


class PennylaneAuthError(PennylaneError):
	"""401 — Invalid or expired token."""


class PennylanePermissionError(PennylaneError):
	"""403 — Missing required scope."""


class PennylaneNotFoundError(PennylaneError):
	"""404 — Resource not found."""


class PennylaneValidationError(PennylaneError):
	"""422 — Validation failure."""

	def __init__(self, message, status_code=422, response=None, details=None):
		super().__init__(message, status_code, response)
		self.details = details or []


class PennylaneRateLimitError(PennylaneError):
	"""429 — Rate limit exceeded."""


class PennylaneServerError(PennylaneError):
	"""5xx — Pennylane server error."""
