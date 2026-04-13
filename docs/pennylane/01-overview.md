# Pennylane API — Overview, Concepts & Glossary

← [Index](./00-index.md)

---

## What is the Pennylane API?

Pennylane is an all-in-one financial and accounting OS for SMEs and accounting firms (French market, PCG-compliant). Its API lets developers, accounting firms, and integration partners:

- Manage sales: customer invoices, quotes, customers, products
- Manage purchases: supplier invoices, suppliers
- Create and retrieve accounting entries (ledger entries, journals)
- Generate accounting reports (trial balance, FEC, analytical ledger)
- Manage banking: bank accounts, transactions, payment matching
- Manage analytics: categories and category groups
- Track changes for incremental sync

---

## API Types

Three distinct APIs — choose based on your role:

### 1. Company API
| | |
|--|--|
| **Target** | Companies and integration partners |
| **Auth** | Company API Token or OAuth 2.0 |
| **Plan required** | Essential or higher |
| **Capabilities** | Manage sales, purchases, accounting entries, reports, analytical tags |
| **Docs** | `pennylane.readme.io` |

### 2. Firm API
| | |
|--|--|
| **Target** | Accounting firms and integration partners |
| **Auth** | Firm API Token or Firm OAuth |
| **Plan required** | Firm account |
| **Capabilities** | Access client company portfolio, consolidated reports, accounting entries |
| **Docs** | `firm-pennylane.readme.io` |

### 3. Firm Group API
| | |
|--|--|
| **Target** | Accounting firms (advanced scenarios) |
| **Auth** | Firm Group Token or OAuth 2.0 |
| **Access** | Available on request (contact Support or Account Manager) |
| **Capabilities** | Create companies and users within firm context |

---

## Glossary

| API Term | French | Definition |
|----------|--------|------------|
| Customer Invoice | Facture de vente | Invoice billed to a client |
| Credit Note | Avoir | Cancelled/reversed customer invoice |
| Estimate / Quote | Devis | A quote for potential customers |
| Ledger Account | Compte comptable | Accounting account; regulated by French PCG (Plan Comptable Général) |
| Categories | Catégories / axes analytiques | Analytical classification of invoices, transactions, ledger entries |
| Ledger Entry | Pièce comptable | Accounting entry containing multiple entry lines |
| Ledger Entry Line | Ligne d'écriture | Smallest element of a ledger entry; total debit must equal total credit |
| Supplier Invoice | Facture d'achats | Invoice of purchased items billed by a supplier |
| Trial Balance | Balance générale | Accounting balance of all ledger accounts with their totals |
| Fiscal Year | Année fiscale | Year within which accounting happens for a particular exercise |

### Common Ledger Account Prefixes (PCG)
| Prefix | Purpose |
|--------|---------|
| `401` | Suppliers (fournisseurs) |
| `411` | Customers (clients) |
| `4191` | Downpayments received (acomptes reçus) |
| `445x` | VAT accounts |
| `4456` | VAT recoverable (deductible) |
| `4457` | VAT collected (output) |
| `511x` | Cash on hand |
| `512` | Bank (banque) |
| `530` | Cash (caisse) |
| `60x` | Purchase expenses |
| `606–607` | Goods purchases |
| `658` | Miscellaneous expenses (rounding) |
| `706–707` | Revenue / Sales (produits) |
| `758` | Miscellaneous income (rounding) |

---

## Key Concepts

### Payment vs Matched Transaction
- **Payment**: Invoice paid through Pennylane's integrated methods (Qonto, payment links, GoCardless, Stripe). Match is **automatic**.
- **Matched Transaction**: Payment happened outside Pennylane (e.g., bank transfer). Match must be done **manually** via app or API.

### Import vs Create (Customer Invoice)
- **Import**: Bring in an invoice created in another tool. Requires PDF upload + all data manually provided. Does NOT use OCR.
- **Create**: Generate a new invoice via Pennylane's invoice editor. PDF is auto-generated. Finalized by default (use `"draft": true` to keep editable).

### Amounts as Strings
All numeric/amount fields must be sent as **strings**: `"100.00"`, never `100.00`. This prevents float precision errors.

---

## Sandbox Environment

| User type | How to get sandbox |
|-----------|-------------------|
| Companies | Account profile → "Test environment" (creates separate sandbox account) |
| Firms | Use existing firm account directly — no sandbox needed |
| Integration partners | Email `partnerships@pennylane.com` |

**Before testing invoice functionality, configure:**
- Company address and contact details
- Bank account details
- Company logo
- Sequential invoice numbering (legally required in France)

---

## Data Sharing vs API

| Feature | Data Sharing | API |
|---------|-------------|-----|
| Access type | Read-only | Read/write |
| Data freshness | Few hours delay | Real-time |
| Dataset size | Optimized for very large datasets | Small to medium datasets |
| BI tools support | Yes (Power BI, Tableau) | No |
| Setup effort | Minimal | Developer setup required |

**Decision guide:**
- Analytics at scale → Data Sharing
- Automation & integration → API
- Both → Combine (Data Sharing for bulk analytics, API for live two-way actions)

---

## Supported Integration Use Cases

- Point of Sale (POS) — Ticket Z as ledger entries
- Accounting reporting — trial balance, FEC export
- Invoicing management — import/create customer & supplier invoices
- Incremental sync — change tracking via changelog endpoints
- Payment matching — automatic reconciliation with Stripe, GoCardless, bank transfers
