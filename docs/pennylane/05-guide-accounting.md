# Pennylane API — Guide: Accounting Use Cases

← [Index](./00-index.md)

Covers: creating ledger entries, POS / Ticket Z integration, accounting reporting strategy.

---

## 1. Create Ledger Entries

**When to use:** Record custom accounting entries — payroll, adjustments, external system imports.

**Required scope:** `ledger_entries:all`  
**Optional scope:** `file_attachments:all` (for supporting documents)

### Step 1 — Get Journals
```bash
curl https://app.pennylane.com/api/external/v2/journals \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Common journal codes: `VT` (sales), `HA` (purchases), `BQ` (bank), `OD` (general)

**Store journal IDs per tenant** — they differ across companies.

**Create a custom journal if needed:**
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/journals \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"code": "PAYE", "label": "Payroll Journal"}'
```

### Step 2 — Get Ledger Accounts
```bash
curl "https://app.pennylane.com/api/external/v2/ledger_accounts?filter=[{\"field\":\"number\",\"operator\":\"start_with\",\"value\":\"512\"}]" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Critical:** The same account number may exist with multiple IDs, one per VAT rate. Select the ID matching your required VAT configuration.

Common account prefixes:
- `401` — Suppliers
- `411` — Customers  
- `512` — Bank
- `60x–607` — Purchase expenses
- `706–707` — Revenue

### Step 3 — Create the Entry
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/ledger_entries \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-01-15",
    "label": "Customer payment - ACME Corp",
    "journal_id": 42,
    "ledger_entry_lines": [
      {
        "debit": "1000.00",
        "credit": "0.00",
        "ledger_account_id": 512001,
        "label": "Bank receipt"
      },
      {
        "debit": "0.00",
        "credit": "1000.00",
        "ledger_account_id": 411001,
        "label": "Customer account"
      }
    ]
  }'
```

**Critical:** Total debits must exactly equal total credits. Returns `422` if not.  
All amounts are strings. Use `"0.00"` for the side with no entry.

### Step 4 — Attach Supporting Document (Optional)

1. Upload file:
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/file_attachments \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F file=@supporting-doc.pdf
```

2. Include `file_attachment_id` in the ledger entry payload (Step 3).

### Step 5 — Multi-Currency (Optional)

Add `"currency": "USD"` to the entry payload. Exchange rate defaults to `1.0`.

### Step 6 — Track Changes
```bash
curl "https://app.pennylane.com/api/external/v2/changelogs/ledger_entry_lines?start_date=2025-01-01T00:00:00Z" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Common Errors

| Status | Cause | Fix |
|--------|-------|-----|
| `400` | Invalid payload | Verify JSON |
| `401` | Expired token | Refresh auth |
| `403` | Missing scope | Add `ledger_entries:all` |
| `404` | Invalid journal/account ID | Verify IDs |
| `422` | Debits ≠ Credits | Recalculate |

---

## 2. POS Integration — Ticket Z

**When to use:** Connect a Point of Sale system by posting daily sales reports (Ticket Z) as balanced ledger entries.

**Required scope:** `ledger`  
**Optional scope:** `file_attachments:all`

**Key rule:** Journal and ledger account IDs differ per company. **Store them per tenant.**

### Step 1 — Verify Authentication
```bash
curl https://app.pennylane.com/api/external/v2/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Step 2 — Get or Create POS Journal
```bash
# List journals
curl https://app.pennylane.com/api/external/v2/journals \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Create dedicated POS journal
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/journals \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"code": "POS01", "label": "POS Cash Journal"}'
```

### Step 3 — Map Ledger Accounts

Revenue accounts (`706`/`707`):
```bash
curl "https://app.pennylane.com/api/external/v2/ledger_accounts?filter=[{\"field\":\"number\",\"operator\":\"start_with\",\"value\":\"706\"}]" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

VAT output accounts (`4457`):
```bash
curl "https://app.pennylane.com/api/external/v2/ledger_accounts?filter=[{\"field\":\"number\",\"operator\":\"start_with\",\"value\":\"4457\"}]" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Payment/cash accounts (`511`/`530`):
```bash
curl "https://app.pennylane.com/api/external/v2/ledger_accounts?filter=[{\"field\":\"number\",\"operator\":\"start_with\",\"value\":\"53\"}]" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Step 4 — Handle Rounding

Entries must balance: `Sum(Credits) = Revenue + VAT`, `Sum(Debits) = Payments`

| Situation | Fix |
|-----------|-----|
| Credits < Debits | Add credit line to account `758` (misc. income) |
| Debits < Credits | Add debit line to account `658` (misc. expense) |

### Step 5 — Attach Ticket Z PDF (Optional)
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/file_attachments \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F file=@ticket-z.pdf
```

### Step 6 — Post Ledger Entry
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/ledger_entries \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-01-01",
    "label": "Ticket Z – Main Register – 2025-01-01",
    "journal_id": <JOURNAL_ID>,
    "ledger_entry_lines": [
      {"debit": "0.00",   "credit": "90.91", "ledger_account_id": <REVENUE_ID>},
      {"debit": "0.00",   "credit": "9.09",  "ledger_account_id": <VAT_ID>},
      {"debit": "100.00", "credit": "0.00",  "ledger_account_id": <PAYMENT_ID>}
    ]
  }'
```

Expected response: `201 Created`

### Step 7 — Validate Entry
```bash
curl "https://app.pennylane.com/api/external/v2/ledger_entries?filter=[{\"field\":\"date\",\"operator\":\"eq\",\"value\":\"2025-01-01\"},{\"field\":\"journal_id\",\"operator\":\"eq\",\"value\":<JOURNAL_ID>}]" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Best Practices
- One account mapping per company; reuse thereafter
- One entry per business cycle (daily or per shift)
- Attach Ticket Z PDF for audit trail
- Use stable, unique labels for idempotency
- Never duplicate entries for the same shift

---

## 3. Accounting Reporting Strategy

**Goal:** Extract accounting data efficiently without overloading the API.

**Warning:** Do NOT repeatedly fetch all ledger entry lines — this can time out for high-volume companies.

### Recommended Architecture

**Phase 1 — Initial bulk export (one-time):**
Use the FEC export (`exports:fec` scope) or analytical general ledger export (`exports:agl`), or Data Sharing for large datasets.

**Phase 2 — Incremental sync:**
Use the changelog to fetch only what changed:
```bash
curl "https://app.pennylane.com/api/external/v2/changelogs/ledger_entry_lines?start_date=2025-10-01T00:00:00Z" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Phase 3 — Batch fetch changed records:**
Collect IDs from changelog, then:
```bash
GET /api/external/v2/ledger_entries?filter=[{"field":"id","operator":"in","value":[123,456,789]}]
```

### Available Reporting Endpoints

| Endpoint | Scope | Description |
|----------|-------|-------------|
| `GET /trial_balance` | `trial_balance:readonly` | Balance by ledger account for a period |
| `GET /fiscal_years` | `fiscal_years:readonly` | List fiscal years |
| FEC export | `exports:fec` | French tax audit file |
| AGL export | `exports:agl` | Analytical general ledger |

### Trial Balance Example
```bash
curl "https://app.pennylane.com/api/external/v2/trial_balance?period_start=2025-01-01&period_end=2025-12-31" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
