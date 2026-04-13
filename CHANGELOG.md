# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-04-13

First production release.

### Added

- **Pennylane Customer** — push on save, pull via hourly changelog. Supports both `company` and `individual` customer types routed to their respective API endpoints (`/company_customers`, `/individual_customers`).
- **Pennylane Product** — push on save, pull via hourly changelog.
- **Pennylane Customer Invoice** — push on save/submit, pull via hourly changelog and webhook. Submittable DocType; PDF attached on pull and never re-downloaded if already present.
- **Pennylane Customer Quote** — push on save, pull via hourly changelog and webhook. Non-submittable DocType; fields are conditionally read-only when status is `accepted`, `denied`, `invoiced`, or `expired`. PDF is replaced on every pull to reflect the latest version.
- **Pennylane Customer Contact** — read-only child table on Customer, synced during customer pull.
- **Pennylane Sync Queue** — outbox retry queue for failed push jobs (up to 5 retries, exponential back-off with jitter).
- **Pennylane Sync Log** — full audit trail for every push and pull operation.
- **Pennylane Settings** — single DocType for API credentials, webhook configuration, resource toggles, force full sync, cursor management and log retention. API token is required; company ID is auto-populated via the Test Connection action.
- **Webhook receiver** — HMAC-SHA256 signature verification (checked before evaluating any application state), event deduplication via Redis (60 s TTL), returns `200 OK` when webhooks are disabled so Pennylane does not retry.
- **Automatic webhook registration** — enabling the webhook toggle in Settings auto-registers the subscription with Pennylane and stores the signing secret; disabling it deregisters automatically.
- **Force full re-sync** — per-resource full import triggered from the Settings UI; protected by a Redis concurrency lock so concurrent runs are rejected.
- **Hourly pull jobs** — each resource type is enqueued independently on the `long` queue with a 1 500 s timeout, decoupled from the 300 s scheduler worker limit.
- **PDF attachment helper** — downloads and attaches Pennylane PDFs; idempotent for invoices (skips if already attached), replaces for quotes (content may change on update).
- **French translations** — `fr.csv` covers all user-visible strings including status labels and UI buttons.
- **Open in Pennylane button** — direct link to the corresponding record in the Pennylane web app, available on all four DocType forms.
- **Search indexes** — `pennylane_id` indexed on all resource DocTypes; `resource_type`, `frappe_docname`, `status`, and `next_retry_at` indexed on the Sync Queue.
- **Uninstall cleanup** — `before_uninstall` deregisters the webhook subscription from Pennylane before removing local UI artifacts.

### Security

- Webhook HMAC verification runs before any application logic; an invalid or missing signature returns `401` without leaking whether webhooks are enabled.
- Redis deduplication guard prevents duplicate processing of the same event within 60 seconds.
