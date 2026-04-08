<div align="center">

# Pennylane

**Pennylane integration for the Frappe ecosystem.**

[![Python](https://img.shields.io/badge/python-3.14+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Frappe](https://img.shields.io/badge/frappe-v16-0089ff?style=flat-square)](https://frappeframework.com)
[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](license.txt)

*A project by [Underscore Blank OÜ](mailto:contact@underscore-blank.io)*

</div>

---

## About

**Pennylane** is a standalone Frappe app that bridges [Pennylane](https://www.pennylane.com) — a modern French accounting platform — with the Frappe ecosystem. It has **no ERPNext dependency** and works with any Frappe v16 installation.

It provides native Frappe DocTypes for all Pennylane resources, bidirectional sync via the Pennylane API v2, real-time webhook support, and built-in observability tools.

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

- **Incremental sync** — changelog-based cursor per resource type; only changed records are fetched.
- **Force full sync** — Settings UI lets you reset cursors and re-import any resource from scratch.
- **Retry queue** — failed jobs land in `Pennylane Sync Queue` and are retried up to 5 times with back-off.
- **Real-time webhooks** — `customer_invoice.created` and `quote.created` events trigger an immediate pull without waiting for the hourly job.
- **Dependency resolution** — pushing an invoice automatically syncs its customer first if not yet known to Pennylane.

### Invoice & Quote lifecycle (Submittable DocTypes)

Invoices and quotes use Frappe's **submittable** DocType pattern:

| Frappe state | Meaning |
|---|---|
| `docstatus = 0` — Draft | Editable; pushed to Pennylane with `draft: true` |
| `docstatus = 1` — Submitted | Read-only; pushed to Pennylane as finalized on submit |
| `docstatus = 2` — Cancelled | Cancelled in Frappe; Pennylane action is manual |

Quotes are auto-submitted when Pennylane moves them to `accepted`, `denied`, `invoiced`, or `expired`. A quote can originate one or many invoices; each invoice carries a `source_quote` link back.

### PDF attachments

On every pull, if Pennylane returns a `public_file_url`, the PDF is downloaded and attached to the Frappe document. If an attachment with the same filename already exists it is replaced, so the file always reflects the latest version.

### Notifications

When a sync failure persists after retries, all active System Manager users receive a Frappe Notification Log entry and a real-time desk notification.

---

## DocTypes

```
Pennylane Settings           — API credentials, sync toggles, webhook secret
Pennylane Customer           — Company or individual customer
Pennylane Customer Contact   — Read-only contacts child table on Customer
Pennylane Product            — Sellable product / service
Pennylane Invoice Line       — Shared child table for Invoice and Quote lines
Pennylane Customer Invoice   — Customer invoice (submittable)
Pennylane Customer Quote     — Customer quote / estimate (submittable)
Pennylane Sync Queue         — Retry queue for failed push jobs
Pennylane Sync Log           — Audit log for every sync operation
```

---

## Architecture

```
pennylane/
├── api/
│   ├── sync.py          # Whitelisted endpoints for manual sync triggers
│   └── webhook.py       # Guest-whitelisted Pennylane webhook receiver
├── client/
│   ├── base.py          # PennylaneClient — HTTP, rate-limiting, pagination
│   ├── customers.py
│   ├── invoices.py
│   ├── products.py
│   └── quotes.py
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
└── tasks.py             # Scheduled jobs (hourly pull, retry queue)
```

---

## Configuration

### 1. Install the app

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench --site your.site install-app pennylane
```

### 2. Set up credentials

Open **Pennylane Settings** in the Frappe desk and fill in:

| Field | Description |
|---|---|
| API Token | Your Pennylane developer token |
| Webhook Secret | Secret used to verify incoming webhook signatures |
| Sync Customers / Products / Invoices / Quotes | Enable per-resource sync |
| Notify on Sync Failure | Send desk notifications when sync fails persistently |

### 3. Register the webhook in Pennylane

Point your Pennylane webhook subscription to:

```
https://your.site/api/method/pennylane.api.webhook.handle_webhook
```

Supported events: `customer_invoice.created`, `quote.created`.

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

## License

Distributed under the **AGPL-3.0** License. See [`license.txt`](license.txt) for details.

---

<div align="center">
  <sub>Maintained by <a href="mailto:contact@underscore-blank.io">Underscore Blank OÜ</a></sub>
</div>
