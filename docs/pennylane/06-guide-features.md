# Pennylane API — Guide: Features

← [Index](./00-index.md)

Covers: payment matching, change tracking, send by email, downpayment invoices, VAT rates & ledger accounts, migration v1→v2.

---

## 1. Payment Matching

Automatically reconcile invoices with payments using the `transaction_reference` object in the invoice payload.

To **disable** automatic matching: leave all `transaction_reference` fields empty.

### Method 1 — Invoice Number (Any Bank)

Matches when the invoice number appears in the bank transfer label.

```json
"transaction_reference": {
  "banking_provider": "bank",
  "provider_field_name": "label",
  "provider_field_value": "invoice_number"
}
```

You can also use any custom unique reference that will appear in the transfer label instead of `"invoice_number"`.

### Method 2 — Stripe

| `provider_field_name` | Format | Description |
|----------------------|--------|-------------|
| `payment_id` | `pi_XXXX` | Stripe Payment Intent |
| `charge_id` | `ch_XXXX` | Stripe Charge |
| `report_id` | `frr_XXXX` | Stripe aggregated report |

```json
"transaction_reference": {
  "banking_provider": "stripe",
  "provider_field_name": "payment_id",
  "provider_field_value": "pi_3ABC123xyz"
}
```

### Method 3 — GoCardless

```json
"transaction_reference": {
  "banking_provider": "gocardless",
  "provider_field_name": "payment_id",
  "provider_field_value": "PM00XXXXXXX"
}
```

---

## 2. Change Tracking (Incremental Sync)

Use changelog endpoints to monitor resource changes without repeatedly fetching all records.

**Endpoint:** `GET /api/external/v2/changelogs/{resource_type}`

**Available resource types:** `customer_invoices`, `supplier_invoices`, `customers`, `suppliers`, `products`, `ledger_entry_lines`, `transactions`

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `start_date` | ISO 8601 datetime. Without it: last 4 weeks only. |
| `limit` | Default 20, max 1000 |
| `cursor` | Pagination cursor |

**Response items:**
```json
{
  "id": 456,
  "resource_id": 9876,
  "operation": "update",
  "processed_at": "2025-10-15T14:32:00Z"
}
```

Operations: `insert`, `update`, `delete`

**Sync loop:**
1. Store `processed_at` of last processed change
2. Poll changelog using that timestamp as `start_date`
3. Collect all changed `resource_id`s
4. Batch fetch via `in` filter:
```
GET /customer_invoices?filter=[{"field":"id","operator":"in","value":[id1,id2,...]}]
```

**Limits:**
- Changes older than **4 weeks** are not retrievable
- Deleted resources return `404` — handle gracefully

---

## 3. Send Documents by Email

Send invoices or quotes to customers after creation or import.

**Endpoints:**
- `POST /api/external/v2/customer_invoices/{id}/send_by_email`
- `POST /api/external/v2/quotes/{id}/send_by_email`

**Timing issue:** PDF generation takes a few minutes after creation. Calling too soon returns `409 Conflict`. Retry after a few minutes.

**Success:** `204 No Content` — email is queued.

**Recipient rules:**
- If no recipients specified → uses customer's email addresses on file
- Customer must have an email address
- CC/BCC not supported via API

**Email details:**
- Sender: `[email protected]`
- Reply-to: address set in Pennylane under "Paramètres > Facturation clients"
- Templates: platform defaults; auto-selects FR or EN based on customer's billing language
- Templates cannot be customized via API

---

## 4. Downpayment Invoices (Factures d'acompte)

**Use the import endpoint** — not the create endpoint.  
Using create results in a regular invoice (not shown as downpayment in UI).

**Ledger account for downpayments:** `4191`

### Step 1 — Import the Downpayment Invoice

```bash
POST /api/external/v2/customer_invoices/import
```

Payload: one invoice line with `"ledger_account_id"` set to the account with number `4191`.

### Step 2 — Import the Final Invoice

Payload includes:
- All standard invoice lines
- One **negative** line matching the downpayment amount, with `ledger_account_id` pointing to account `4191`

Using `4191` ensures Pennylane displays the invoice as a downpayment in the UI and categorizes it correctly.

---

## 5. VAT Rates & Ledger Accounts

Each VAT rate requires a distinct ledger account item with a unique ID in Pennylane's system.

### VAT Rate Codes

| Code | Rate | Notes |
|------|------|-------|
| `FR_200` | 20% | Standard VAT — shows green in UI |
| `FR_100` | 10% | Reduced VAT — shows green |
| `FR_055` | 5.5% | Reduced VAT — shows green |
| `exempt` | 0% | VAT exempt — shows green |
| `any` | N/A | Unspecified — shows red "N/A" in UI. Avoid for proper accounting. |

### Finding the Right Account ID

Same account number (e.g., `706000000009`) can have multiple IDs:

| ID | VAT Rate | UI |
|----|----------|----|
| 1326475509 | `FR_200` | Green |
| 1326475560 | `any` | Red N/A |
| 1326475596 | `exempt` | Green |

**Query to find accounts by number:**
```bash
curl "https://app.pennylane.com/api/external/v2/ledger_accounts?filter=[{\"field\":\"number\",\"operator\":\"start_with\",\"value\":\"706000000009\"}]" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Select the ID with the matching `vat_rate` field.

**Create a missing account variant:**
```bash
curl --request POST \
  --url https://app.pennylane.com/api/external/v2/ledger_accounts \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"number": "706000000009", "label": "Sales revenue", "vat_rate": "FR_200"}'
```

---

## 6. Migration: API v1 → v2

**v1 deprecation:** End of 2025. v2 is the current stable version.  
**v1 responses now include a `v2_id` field** to help with mapping.

### Breaking Changes Summary

| Topic | v1 | v2 |
|-------|----|----|
| ID system | `source_id` supported | Internal IDs only |
| Scopes | Coarse (e.g., `customer_invoices`) | Granular (e.g., `customer_invoices`, `products`, `customers`, `file_attachments` separately) |
| Resource creation | Multiple types in one call | One resource per call (create customer first, then invoice) |
| Pagination | Page-number based | Cursor-based |
| File uploads | Base64 or URL directly | Upload to `/file_attachments` first; reference `file_attachment_id` |
| Numeric amounts | Floats accepted | **Must be strings** (`"100.00"`) |

### Attribute Renames

| v1 Name | v2 Name |
|---------|---------|
| `plan_item` | `ledger_account` |
| `customer_validation_needed` | `import_as_incomplete` |
| `Estimates` | `Quotes` |

### Migration Steps

1. Generate new Company API token with granular v2 scopes
2. Update all `source_id` references to use `id` (from `v2_id` mapping)
3. Split multi-resource creation calls into separate sequential calls
4. Replace page-number pagination with cursor-based pagination
5. Switch file handling to upload-then-reference pattern
6. Convert all numeric amount fields to strings
7. Update renamed attributes in payloads
8. Test in sandbox before production cutover
