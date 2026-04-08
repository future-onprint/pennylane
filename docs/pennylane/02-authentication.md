# Pennylane API — Authentication & Scopes

← [Index](./00-index.md)

All requests require:
```
Authorization: Bearer <YOUR_TOKEN>
```

---

## 1. Company API Token

**Prerequisites:** Essential plan or higher + Admin role (Executive, Internal Accountant, or External Accountant).

### Generate a Token
1. Log in to Pennylane
2. Management → Settings → Connectivity → Developers
3. Click **"Generate an API Token"**
4. Enter a descriptive name (e.g., `"CRM sync"`)
5. Select permission level under API V2:
   - **Read only** — retrieve data
   - **Read and write** — create/update data
6. Choose expiration: 1 month / 6 months / 12 months / Unlimited
7. Click **Generate Token**
8. **Copy immediately** — shown only once, never stored by Pennylane

### Security Rules
- Store in a secrets manager; never commit to version control
- Create separate tokens per application/environment
- Revoke unused tokens immediately
- Deletion is irreversible — integrations break until replaced

### Token Management
From the Developers tab: view name, scopes, creation/expiration dates, last usage timestamp.

---

## 2. Firm API Token

Generated from the firm account. See `firm-pennylane.readme.io` for full steps.

---

## 3. OAuth 2.0

For integration partners building third-party apps and accounting firms using the Firm API.

**Flow:** Authorization Code (6 steps)

1. User initiates sign-in in your app
2. User grants access → Pennylane returns authorization code
3. Exchange code for access token + refresh token
4. Use access token in API calls
5. Refresh token before it expires
6. Revoke token when access ends

### Endpoints

| Step | Method | URL |
|------|--------|-----|
| Authorization | GET | `https://app.pennylane.com/oauth/authorize` |
| Token exchange | POST | `https://app.pennylane.com/oauth/token` |
| Token revocation | POST | `https://app.pennylane.com/oauth/revoke` |

### Authorization Request (GET) Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `client_id` | Yes | Your registered application ID |
| `redirect_uri` | Yes | Post-approval redirect URL |
| `response_type` | Yes | Must be `code` |
| `scope` | Yes | Space-separated list of scopes |
| `state` | Recommended | Random token for CSRF protection |

### Token Exchange (POST) Parameters

| Parameter | Description |
|-----------|-------------|
| `client_id` | Your application ID |
| `client_secret` | Your application secret |
| `code` | Authorization code received |
| `redirect_uri` | Same URI as authorization step |
| `grant_type` | Must be `authorization_code` |

### Refresh Token (POST) Parameters

| Parameter | Description |
|-----------|-------------|
| `client_id` | Your application ID |
| `client_secret` | Your application secret |
| `refresh_token` | Current refresh token |
| `grant_type` | Must be `refresh_token` |

### Token Lifetimes

| Token | Lifetime | Notes |
|-------|----------|-------|
| Access token | 24 hours | Must be refreshed after expiry |
| Refresh token | 90 days | Each use revokes the previous token |

### Best Practices
- Validate `state` parameter to prevent CSRF
- Store token creation time; refresh before expiry
- Request only minimal required scopes
- Never expose `client_secret` client-side
- Revoke tokens when integration ends

---

## 4. Scopes Reference

Pattern: `resource:readonly` (read) or `resource:all` (read + write)

### Sales
| Scope | Access |
|-------|--------|
| `customers:readonly` | Read customers |
| `customers:all` | Full customer management |
| `products:readonly` | Read products |
| `products:all` | Full product management |
| `customer_invoices:readonly` | Read customer invoices |
| `customer_invoices:all` | Create/update customer invoices |
| `quotes:readonly` | Read quotes |
| `quotes:all` | Full quote management |
| `customer_mandates:readonly` | Read SEPA mandates |
| `customer_mandates:all` | Full SEPA mandate management |
| `billing_subscriptions:readonly` | Read recurring billing |
| `billing_subscriptions:all` | Full recurring billing management |
| `commercial_documents:readonly` | Read commercial documents |
| `commercial_documents:all` | Full commercial document management |
| `customer_invoice_templates:readonly` | View invoice templates |

### Purchases
| Scope | Access |
|-------|--------|
| `suppliers:readonly` | Read suppliers |
| `suppliers:all` | Full supplier management |
| `supplier_invoices:readonly` | Read supplier invoices |
| `supplier_invoices:all` | Create/import supplier invoices |
| `purchase_requests:readonly` | Read purchase requests |
| `purchase_requests:all` | Full purchase request management |

### Accounting
| Scope | Access |
|-------|--------|
| `ledger` | Full journal + ledger entry management (legacy, prefer granular scopes) |
| `trial_balance:readonly` | Retrieve trial balance |
| `exports:fec` | FEC fiscal export |
| `exports:agl` | Analytical general ledger export |
| `fiscal_years:readonly` | Read fiscal years |
| `journals:readonly` | Read journals |
| `journals:all` | Full journal management |
| `ledger_accounts:readonly` | Read ledger accounts |
| `ledger_accounts:all` | Full ledger account management |
| `ledger_entries:readonly` | Read ledger entries |
| `ledger_entries:all` | Create/update ledger entries |

### Analytics
| Scope | Access |
|-------|--------|
| `categories:readonly` | Read analytical categories |
| `categories:all` | Full category management |

### Banking
| Scope | Access |
|-------|--------|
| `transactions:readonly` | Read transactions |
| `transactions:all` | Full transaction management |
| `bank_accounts:readonly` | Read bank accounts |
| `bank_accounts:all` | Full bank account management |
| `bank_establishments:readonly` | Read bank establishments |

### Core / Shared
| Scope | Access |
|-------|--------|
| `file_attachments:readonly` | Read file attachments |
| `file_attachments:all` | Upload and manage file attachments |
