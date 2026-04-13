<div align="center">

# 🪙 Pennylane

**Pennylane integration for the Frappe ecosystem.**

[![Python](https://img.shields.io/badge/python-3.14+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Frappe](https://img.shields.io/badge/frappe-v16-0089ff?style=flat-square)](https://frappeframework.com)
[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](license.txt)

*A project by [Underscore Blank OÜ](mailto:contact@underscore-blank.io)*

</div>

---

## About

**Pennylane** is a standalone Frappe app that bridges [Pennylane](https://www.pennylane.com) — a modern French accounting platform — with the Frappe ecosystem. It has **no ERPNext dependency** and works with any Frappe v16 installation.

It provides native Frappe DocTypes for all Pennylane resources, bidirectional sync via the Pennylane API v2, automatic webhook registration, and built-in observability tools.

---

## Features

### Resources

| DocType | Push (Frappe → Pennylane) | Pull (Pennylane → Frappe) |
|---|---|---|
| **Pennylane Customer** | ✓ on save | ✓ hourly changelog |
| **Pennylane Product** | ✓ on save | ✓ hourly changelog |
| **Pennylane Customer Invoice** | ✓ on save / submit | ✓ hourly changelog + webhook |
| **Pennylane Customer Quote** | ✓ on save | ✓ hourly changelog + webhook |
| **Pennylane Customer Contact** | — (API read-only) | ✓ on customer pull |

### Sync mechanics

- **Incremental sync** — changelog-based cursor per resource type; only changed records are fetched each hour.
- **Independent pull jobs** — each resource type is enqueued as its own background job on the `long` queue with a 1 500 s timeout, so a slow changelog never blocks the others.
- **Force full sync** — Settings UI lets you reset cursors and re-import any resource from scratch; concurrent runs are rejected via a Redis lock.
- **Retry queue** — failed push jobs land in `Pennylane Sync Queue` and are retried up to 5 times with exponential back-off and jitter.
- **Real-time webhooks** — `customer_invoice.created` and `quote.created` events trigger an immediate pull without waiting for the hourly job.
- **Dependency resolution** — pushing a quote or invoice automatically syncs its customer first if not yet known to Pennylane.

### Customer types

Both `company` and `individual` customers are supported. Push and pull are routed to the correct Pennylane endpoint (`/company_customers` or `/individual_customers`) based on the `customer_type` field.

### Invoice lifecycle

Invoices use Frappe's **submittable** DocType pattern:

| Frappe state | Meaning |
|---|---|
| `docstatus = 0` — Draft | Editable; pushed to Pennylane with `draft: true` |
| `docstatus = 1` — Submitted | Read-only; finalized in Pennylane on submit |
| `docstatus = 2` — Cancelled | Cancelled in Frappe; Pennylane action is manual |

### Quote lifecycle

Quotes are **not submittable**. They remain in `docstatus = 0` at all times and are always editable in Frappe — unless Pennylane has locked them. Fields become read-only automatically when the Pennylane status is `accepted`, `denied`, `invoiced`, or `expired`. A quote can originate one or many invoices; each invoice carries a `source_quote` link back.

### PDF attachments

On every pull, if Pennylane returns a `public_file_url`:

- **Invoices** — the PDF is downloaded once and never re-downloaded if already attached (invoices are immutable in Pennylane).
- **Quotes** — the PDF is always replaced because it can be regenerated after each edit.

### Webhook security

- The HMAC-SHA256 signature is verified **before** any application logic executes — an invalid or missing signature returns `401` without leaking whether webhooks are enabled.
- Duplicate events are deduplicated via a Redis key (60 s TTL) to handle Pennylane's at-least-once delivery guarantee.
- When webhooks are disabled, the endpoint returns `200 OK` so Pennylane does not retry.

### Notifications

When a sync failure persists after retries, all active System Manager users receive a Frappe Notification Log entry and a real-time desk notification.

---

## DocTypes

```
Pennylane Settings           — API credentials, sync toggles, webhook config, force full sync
Pennylane Customer           — Company or individual customer
Pennylane Customer Contact   — Read-only contacts child table on Customer
Pennylane Product            — Sellable product / service
Pennylane Invoice Line       — Shared child table for Invoice and Quote lines
Pennylane Customer Invoice   — Customer invoice (submittable)
Pennylane Customer Quote     — Customer quote / estimate (non-submittable, conditionally read-only)
Pennylane Sync Queue         — Retry queue for failed push jobs
Pennylane Sync Log           — Audit log for every sync operation
```

---

## Architecture

```
pennylane/
├── api/
│   └── webhook.py       # Guest-whitelisted Pennylane webhook receiver
├── client/
│   ├── base.py          # PennylaneClient — HTTP, rate-limiting, pagination
│   ├── customers.py
│   ├── invoices.py
│   ├── products.py
│   ├── quotes.py
│   └── webhooks.py      # Webhook subscription management
├── mappers/             # Pure functions: Frappe doc ↔ API payload
│   ├── customer.py
│   ├── invoice.py
│   ├── invoice_line.py
│   ├── product.py
│   └── quote.py
├── sync/                # Orchestration: push, pull, full sync
│   ├── customer.py
│   ├── invoice.py
│   ├── product.py
│   ├── quote.py
│   └── utils.py
├── utils/
│   └── pdf.py           # PDF download and attachment helper
├── hooks.py
└── tasks.py             # Scheduled jobs (hourly pull, retry queue, daily cleanup)
```

---

## Configuration

### 1. Install the app

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench --site your.site install-app pennylane
bench --site your.site migrate
```

### 2. Enter your API credentials

Open **Pennylane Settings** in the Frappe desk:

| Field | Description |
|---|---|
| **API Token** | Your Pennylane developer token (required) |
| **Enable Pennylane Integration** | Master switch — disables all sync when off |
| **Sync Customers / Products / Invoices / Quotes** | Per-resource sync toggles |
| **Notify on Sync Failure** | Send desk notifications when sync fails persistently |

### 3. Test the connection

Click **Test Connection** in Settings. On success the connection status turns green and the **Company ID** field is populated automatically — this ID is required for the "Open in Pennylane" deep links on each DocType form.

### 4. Enable webhooks (optional but recommended)

Toggle **Enable Webhook Reception** in Settings. The app automatically registers a subscription with Pennylane and stores the signing secret. The site must be reachable via HTTPS from the public internet.

Supported events: `customer_invoice.created`, `quote.created`.

To unregister, disable the toggle — the subscription is removed from Pennylane automatically.

### 5. Start the long worker

Pull jobs and full syncs run on the `long` queue. Make sure the worker is started:

```bash
# Development
bench worker --queue long

# Production (Procfile / Supervisor)
# Ensure the long worker is listed alongside default and short
```

---

## Requirements

- [Frappe Bench](https://github.com/frappe/bench) installed and configured
- Frappe Framework **v16**
- Python **≥ 3.14**
- Redis (required by Frappe for the job queue)

---

## Development

This project uses `pre-commit` to enforce code quality:

```bash
cd apps/pennylane
pre-commit install
```

| Tool | Role |
|---|---|
| `ruff` | Python linting and formatting |
| `eslint` | JavaScript linting |
| `prettier` | JavaScript / CSS formatting |
| `pyupgrade` | Python syntax modernization |

Run the test suite against a local bench site:

```bash
bench --site your.site run-tests --app pennylane
```

---

## CI / CD

| Workflow | Trigger |
|---|---|
| **CI** | Push to `develop` — installs app and runs unit tests |
| **Linters** | Pull request — runs Frappe Semgrep Rules and `pip-audit` |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

Distributed under the **AGPL-3.0** License. See [`license.txt`](license.txt) for details.

---

<div align="center">
  <sub>Maintained by <a href="mailto:contact@underscore-blank.io">Underscore Blank OÜ</a></sub>
</div>
