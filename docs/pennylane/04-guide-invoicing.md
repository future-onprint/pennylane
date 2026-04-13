# Pennylane API — Guide: Invoicing Use Cases

← [Index](./00-index.md)

Three invoicing workflows: import supplier invoice, import customer invoice, create customer invoice.

---

## 1. Import a Supplier Invoice

**When to use:** You received a PDF invoice from a supplier and want to record it in Pennylane.

**Required scopes:** `supplier_invoices:all`, `file_attachments:all`  
**Optional scopes:** `ledger_accounts:readonly`, `categories:all`

### Step 1 — Verify Authentication
```bash
curl https://app.pennylane.com/api/external/v2/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Expected: `200 OK`

### Step 2 — Upload the Invoice PDF
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/file_attachments \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: multipart/form-data" \
  -F file=@invoice-october.pdf
```
Returns `{ "id": 13245, ... }` — save this `id`.

Constraints: PDF only, max 100 MB.

### Step 3 — Import the Invoice
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/supplier_invoices/import \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_attachment_id": 13245,
    "supplier_id": 98123,
    "date": "2025-10-01",
    "deadline": "2025-10-31",
    "currency_amount_before_tax": "100.00",
    "currency_tax": "20.00",
    "currency_amount": "120.00",
    "invoice_lines": [
      {
        "ledger_account_id": 601002,
        "currency_amount": "120.00",
        "currency_tax": "20.00",
        "vat_rate": "FR_200"
      }
    ]
  }'
```

**Critical:** Sum of `invoice_lines[].currency_amount` must equal `currency_amount`.  
**Auto deduplication:** Pennylane rejects if the PDF is already in the workspace (`409`).

### Step 4 — Validate
```bash
curl https://app.pennylane.com/api/external/v2/supplier_invoices/4431 \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Step 5 — Categorize (Optional)
```bash
curl --request PUT \
  --url https://app.pennylane.com/api/external/v2/supplier_invoices/4431/categories \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[{"id": 123, "weight": 1.0}]'
```

### Common Errors

| Status | Issue | Fix |
|--------|-------|-----|
| `400` | Invalid payload | Check field names and types |
| `401` | Invalid/expired token | Refresh auth |
| `403` | Missing scope | Add `supplier_invoices:all` |
| `404` | File not found | Re-upload via `/file_attachments` |
| `409` | PDF already exists | Don't re-import same PDF |
| `422` | Line totals don't match | Recalculate |

---

## 2. Import a Customer Invoice

**When to use:** You issued an invoice in another tool and want to import it into Pennylane with the PDF.

**Required scopes:** `customer_invoices:all`, `file_attachments:all`  
**Optional scopes:** `products:readonly`, `ledger_accounts:readonly`, `categories:all`

### Step 1 — Verify Authentication
```bash
curl https://app.pennylane.com/api/external/v2/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Step 2 — Upload the Invoice PDF
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/file_attachments \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: multipart/form-data" \
  -F file=@invoice.pdf
```
Returns `{ "id": 4321, ... }`.

### Step 3 — Import the Invoice
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/customer_invoices/import \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_attachment_id": 4321,
    "customer_id": 1001,
    "date": "2025-10-01",
    "deadline": "2025-10-31",
    "currency_amount_before_tax": "100.00",
    "currency_tax": "20.00",
    "currency_amount": "120.00",
    "invoice_lines": [
      {
        "ledger_account_id": 706002,
        "currency_amount": "120.00",
        "currency_tax": "20.00",
        "quantity": 2,
        "raw_currency_unit_price": "50.00",
        "unit": "piece",
        "vat_rate": "FR_200"
      }
    ]
  }'
```

Notes:
- Ledger accounts: `706xxx` for sales revenue, `445xxx` for VAT
- `import_as_incomplete: true` marks it for accountant review

### Step 4 — Validate
```bash
curl https://app.pennylane.com/api/external/v2/customer_invoices/5678 \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Step 5 — Categorize (Optional)
```bash
curl --request PUT \
  --url https://app.pennylane.com/api/external/v2/customer_invoices/5678/categories \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[{"id": 123, "weight": 1.0}]'
```

### Common Errors

| Status | Issue | Fix |
|--------|-------|-----|
| `401` | Invalid/expired token | Refresh auth |
| `403` | Missing scope | Add `customer_invoices:all` |
| `404` | File expired | Re-upload via `/file_attachments` |
| `422` | Amount mismatch | Recalculate line totals |

---

## 3. Create a Customer Invoice

**When to use:** You want Pennylane to generate the invoice and PDF from structured data.

**Required scope:** `customer_invoices:all`

### Step 1 — Prepare References

Find or create a customer:
```bash
GET /api/external/v2/company_customers
POST /api/external/v2/company_customers
```

Find products (optional):
```bash
GET /api/external/v2/products
```

Find ledger accounts (optional):
```bash
GET /api/external/v2/ledger_accounts?filter=[{"field":"number","operator":"start_with","value":"706"}]
```

### Step 2 — Create the Invoice
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/customer_invoices \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 123,
    "date": "2025-10-01",
    "deadline": "2025-10-31",
    "invoice_lines": [
      {
        "label": "Consulting services",
        "quantity": 2,
        "unit": "hour",
        "raw_currency_unit_price": "100.00",
        "vat_rate": "FR_200"
      }
    ],
    "external_reference": "INV-ACME-2025-001"
  }'
```

Key rules:
- All amounts are **strings** (`"100.00"`, not `100.00`)
- Add `"draft": true` to create a draft; omit for finalized
- Finalized invoices can only be cancelled via credit note

**Response `201`:**
```json
{
  "id": 9876,
  "invoice_number": "INV-2025-001",
  "status": "draft",
  "currency_amount_before_tax": "150.00",
  "currency_tax": "30.00",
  "currency_amount": "180.00"
}
```

### Step 3 — Optional Actions

**Send by email:**
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/customer_invoices/9876/send_by_email \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Note: Call a few minutes after creation — PDF generation takes time. Retry on `409`.

**Categorize:**
```bash
curl --request PUT \
  --url https://app.pennylane.com/api/external/v2/customer_invoices/9876/categories \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[{"id": 123, "weight": 1.0}]'
```

**Check reconciliation:**
```bash
curl https://app.pennylane.com/api/external/v2/customer_invoices/9876/matched_transactions \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Common Errors

| Status | Issue | Fix |
|--------|-------|-----|
| `400` | Invalid payload | Verify field names/formats |
| `401` | Missing/expired token | Refresh credentials |
| `403` | Missing scope | Add `customer_invoices:all` |
| `422` | VAT or totals mismatch | Recalculate amounts |
