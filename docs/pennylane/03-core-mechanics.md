# Pennylane API — Core Mechanics: Errors, Rate Limiting, Pagination, Filtering

← [Index](./00-index.md)

---

## Rate Limiting

**Limit:** 25 requests per 5-second window, per token.

Exceeding returns `HTTP 429`.

### Response Headers (on all responses)

| Header | Description |
|--------|-------------|
| `ratelimit-limit` | Max requests per window (25) |
| `ratelimit-remaining` | Requests remaining in current window |
| `ratelimit-reset` | Unix timestamp when limit resets |

### Additional Headers on 429

| Header | Description |
|--------|-------------|
| `retry-after` | Seconds to wait before retrying |

### Example 429 Response
```
HTTP/2 429 Too Many Requests
retry-after: 2
ratelimit-limit: 25
ratelimit-remaining: 0
ratelimit-reset: 1770379510
```

### Example 200 Response Headers
```
HTTP/2 200 OK
ratelimit-limit: 25
ratelimit-remaining: 23
ratelimit-reset: 1770379510
```

**Strategy:** Use `ratelimit-reset` (not just `retry-after`) to know when quota refreshes. Monitor `ratelimit-remaining` to back off proactively.

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| `200 OK` | Success | — |
| `201 Created` | Resource created | — |
| `204 No Content` | Success, no body (e.g., email dispatch) | — |
| `400 Bad Request` | Malformed JSON, wrong field types, amounts not sent as strings | Fix payload |
| `401 Unauthorized` | Missing, invalid, or expired token | Verify/regenerate token |
| `403 Forbidden` | Valid token lacks required scope | Add missing scope |
| `404 Not Found` | Resource doesn't exist or belongs to different company | Verify endpoint and IDs |
| `409 Conflict` | Duplicate (e.g., same PDF already imported) | Check for existing resource |
| `422 Unprocessable Entity` | Business rule violation (VAT mismatch, unbalanced ledger, duplicate reference) | Inspect `details` field |
| `429 Too Many Requests` | Rate limit exceeded | Wait then retry |
| `500 Internal Server Error` | Unexpected server failure | Retry with exponential backoff |
| `503 Service Unavailable` | Maintenance or outage | Retry with exponential backoff |

### Error Response Format

```json
{
  "error": "machine_readable_code",
  "message": "Human-readable explanation",
  "details": {
    "field": "specific context about the issue"
  }
}
```

### Retry Rules
- **Retry:** `429`, `500`, `503`
- **Do NOT retry without fixing:** `400`, `401`, `403`, `404`, `422`

### Validation Layers
1. **Schema validation** — field types, required fields, JSON structure
2. **Business validation** — totals match, VAT consistent, debit = credit, etc. (most `422` errors come from here)

### Important Notes
- No idempotency enforcement on `/customer_invoices` or `/ledger_entries` — implement deduplication client-side
- Log status code, `error`, `message`, and `details` for every error

---

## Cursor-Based Pagination

Used across all list endpoints.

### Initial Request
```
GET /api/external/v2/customer_invoices
GET /api/external/v2/customer_invoices?limit=50
```

Default limit: `20`. Maximum varies by endpoint (typically 100, some accept up to 1000).

### Response Structure
```json
{
  "items": [...],
  "has_more": true,
  "next_cursor": "eyJpZCI6MTAwfQ=="
}
```

### Subsequent Pages
```
GET /api/external/v2/customer_invoices?cursor=eyJpZCI6MTAwfQ==&limit=50
```

### Rules
- Keep paginating while `has_more` is `true`
- Stop when `next_cursor` is `null`
- Cursors are **temporary** — do not store long-term
- Invalid cursors return `400`
- Use a **consistent `limit`** value across all pages of the same sequence

### Deprecated Pagination (some older endpoints)
Some endpoints still return deprecated fields:
```json
{
  "total_pages": 5,
  "current_page": 1,
  "total_items": 100,
  "per_page": 20
}
```
Use cursor-based fields (`has_more`, `next_cursor`) instead when both are present.

---

## Filtering

Filters are passed as a URL-encoded JSON array in the `filter` query parameter.

### Filter Object Structure
```json
[
  {
    "field": "<resource_field>",
    "operator": "<operator>",
    "value": "<value>"
  }
]
```

### Available Operators

| Operator | Description |
|----------|-------------|
| `eq` | Equal to |
| `not_eq` | Not equal to |
| `lt` | Less than |
| `lteq` | Less than or equal to |
| `gt` | Greater than |
| `gteq` | Greater than or equal to |
| `in` | Included in array |
| `not_in` | Excluded from array |
| `start_with` | Prefix match (ILIKE '123%') |

### Examples

**Single filter — invoices from 2024-01-01:**
```json
[{"field": "date", "operator": "gteq", "value": "2024-01-01"}]
```

**Multiple filters — 2025 invoices from specific customers:**
```json
[
  {"field": "date", "operator": "gteq", "value": "2025-01-01"},
  {"field": "customer_id", "operator": "in", "value": [101, 202]}
]
```

**Ledger accounts by number prefix:**
```
GET /api/external/v2/ledger_accounts?filter=[{"field":"number","operator":"start_with","value":"706"}]
```

**Batch fetch by IDs (for changelog sync):**
```json
[{"field": "id", "operator": "in", "value": [123, 456, 789]}]
```

### Sortable Fields

Most list endpoints support a `sort` parameter:
- Prefix with `-` for descending: `sort=-id` (most recent first)
- Default is usually `-id`

---

## 2026 API Changes (`use_2026_api_changes`)

Many endpoints include a `use_2026_api_changes` query parameter (default: `true`). This flag controls rollout of breaking changes through three phases:

| Phase | Dates | Behavior |
|-------|-------|----------|
| Preview | Before April 7, 2026 | Opt-in via `use_2026_api_changes=true` |
| Sunset | April 8 – June 30, 2026 | New behavior is default; opt-out via `false` |
| Cleanup | From July 1, 2026 | Parameter removed; new behavior is permanent |

The main change: results ordered by descending ID by default.
