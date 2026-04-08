# Pennylane Docs — Index

> API Version: **v2.0** (stable) | v1.0 deprecated end of 2025  
> Base URL: `https://app.pennylane.com/api/external/v2/`  
> Full API reference: [`pennylane.json`](./pennylane.json) (OpenAPI 3.0)

---

## Guides

| File | What it covers |
|------|---------------|
| [01-overview.md](./01-overview.md) | API types (Company / Firm / Firm Group), concepts, glossary, sandbox, data sharing vs API |
| [02-authentication.md](./02-authentication.md) | Company token, Firm token, OAuth 2.0 flow, full scopes reference |
| [03-core-mechanics.md](./03-core-mechanics.md) | Rate limiting, error codes & format, cursor pagination, filter syntax |
| [04-guide-invoicing.md](./04-guide-invoicing.md) | How-to: import supplier invoice, import customer invoice, create customer invoice |
| [05-guide-accounting.md](./05-guide-accounting.md) | How-to: create ledger entries, POS / Ticket Z integration, accounting reporting |
| [06-guide-features.md](./06-guide-features.md) | Payment matching, change tracking, send by email, downpayment invoices, VAT & ledger accounts, migration v1→v2 |

---

## Quick Lookup

**I need to authenticate** → `02-authentication.md`  
**I'm getting a 422 / 401 / 403** → `03-core-mechanics.md`  
**I want to create an invoice** → `04-guide-invoicing.md`  
**I want to import a supplier invoice** → `04-guide-invoicing.md`  
**I want to post accounting entries** → `05-guide-accounting.md`  
**I want to sync data incrementally** → `06-guide-features.md` (Change Tracking)  
**I want to match payments** → `06-guide-features.md` (Payment Matching)  
**I'm building a POS integration** → `05-guide-accounting.md`  
**I need to understand VAT codes** → `06-guide-features.md` (VAT Rates)  
**I'm migrating from v1** → `06-guide-features.md` (Migration v1→v2)  
**I need an endpoint signature** → `pennylane.json` (OpenAPI spec)
