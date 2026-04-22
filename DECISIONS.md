# DECISIONS.md — WorkLog Payment & Settlement

## Problem framing

Freelancers record **multiple time segments** per task (`WorkLog`). Finance pays **monthly remittances** per worker, not per task. The tricky part is **correctness over time**: segments can arrive after a payout, disputes can create **retroactive adjustments**, and **payout attempts can fail** without mutating what is considered “already paid.”

## Schema design rationale

- **`time_entries` carry settlement state** via `settled_remittance_id`, but only after a remittance reaches **`completed`**. Failed attempts create a `remittances` row with `failed` and **do not** attach entries, so operators can retry safely without double-settling.
- **`adjustments` are first-class ledger rows** with optional `relates_to_period_*` metadata for audit. They remain **unapplied** until consumed by the next **successful** remittance (`applied_remittance_id`). This models “October corrections picked up on the November/December run” without reopening October’s remittance.
- **`remittances.total_cents`** is the provider-facing payout amount for that attempt (sum of newly settled eligible entry amounts in-window **plus** all still-unapplied adjustments for that user). This matches the narrative: one ACH per user per run, with prior-period deltas folded in.
- **Exclusions** are modeled two ways: persistent (`time_entries.status = excluded`) and batch-only (`exclude_worklog_ids` / `exclude_user_ids` on `POST /generate-remittances`) so admins can rehearse a window without necessarily rewriting history.

## API & UX choices

- **`GET /worklogs`** returns per–work log rollups (hours + cents + remitted vs unremitted). When `period_start` / `period_end` are supplied, rollups are **scoped to that window** so the admin view matches “what this settlement batch will consider” for list context.
- **`GET /worklogs/{id}`** returns the full segment list for drill-down (supporting investigation and approve/exclude toggles).
- **`PATCH /worklogs/time-entries/{id}`** supports persistent exclusion/approval from the detail screen.
- **`POST /preview-settlement`** accepts the same body as **`POST /generate-remittances`** and returns the **exact per-user payout plan** (time totals, adjustment totals, grand total) **without writing**. The dashboard uses this so “review before confirm” includes **retroactive adjustments** that do not appear on individual worklog rows.
- **CORS** is configurable for local Vite (`5173`) and the Dockerized nginx port (`80`).
- **Period validation**: `period_end` must be on or after `period_start` (`422` on generate/preview, `400` on `GET /worklogs` when both query params are present).

## Assessment coverage (checklist)

| Requirement | Where it lives |
|---------------|----------------|
| List worklogs + earned amount per task | `GET /worklogs` (`amount_cents`, `unremitted_amount_cents`, period-scoped when filtered) |
| Drill down to time entries | `GET /worklogs/{id}` + UI detail route |
| Date range filter for payment window | `period_start` / `period_end` on `GET /worklogs` + UI date inputs |
| Review selection before confirming payment | UI modal + `POST /preview-settlement` |
| Exclude worklogs / freelancers from batch | `exclude_worklog_ids` / `exclude_user_ids` + UI checkboxes |
| Settlement runs (monthly remittance per user) | `POST /generate-remittances` |
| Work evolves after payment | New segments stay unsettled until a later successful run |
| Retroactive adjustments | `adjustments` table + picked up on next successful remittance |
| Failed / cancelled payouts | `failed` remittance does not attach entries; retry safe |
| Overlapping corrections vs new period | Unapplied adjustments fold into the current run’s totals |
| Docker Compose full stack | `docker-compose.yml` + backend/frontend Dockerfiles |
| DECISIONS.md, schema diagram, sample API JSON | This file, `schema.dbml`, `sample-responses.json` |
| Screenshots in PR | Capture list (filters + exclusions), detail, review modal (manual) |

## AGENTS.md guidance

The starter repository did not include an `AGENTS.md`; there were no project-specific agent rules to adopt or reject. Broadly, the implementation favors **small, explicit tables** over event-sourcing, and **idempotent settlement** (entries only link to remittances after success) over compensating transactions, to keep the assessment readable in a single service.

## Edge cases considered

| Scenario | Handling |
|----------|----------|
| New segments after a completed payout | They remain **unsettled** (`settled_remittance_id IS NULL`) and appear in a **later** period’s run when their `occurred_on` falls in that window. |
| Retroactive deduction on old work | Stored as **`adjustments`** with negative `amount_cents`; picked up on the **next successful** remittance for that user. |
| Payout fails | `remittances.status = failed`, entries/adjustments **stay eligible**; a later run retries. |
| Overlapping corrections while running a new period | Unapplied adjustments are **not tied to the remittance period** in logic—only to “next success”—so November work and October adjustments can combine in one attempt. |
| Admin excludes a freelancer for one batch | Request body `exclude_user_ids` removes **both** their in-window entries and their pending adjustments from that **attempt** (adjustments remain in DB if the run fails). |
| Zero or negative totals after netting | Rows with **`total_cents == 0`** are skipped to avoid empty provider calls; large negative-only scenarios would need product rules (not required here). |

## Docker & configuration

- **`docker compose up`** starts Postgres (healthcheck; host port **`5433` → container 5432** to avoid clashing with a local Postgres on 5432), the FastAPI service on **8000**, and the static UI on **5173** (nginx serving the Vite build).
- **`PAYOUT_SIMULATE_FAILURE=true`** demonstrates failed attempts without touching entry settlement state.
- Seed data is loaded from **`seed/worklogs.json`** on first boot when tables are empty.

## Follow-ups if this were production

- Double-entry ledger + immutable `remittance_line_items` for accounting exports.
- Stronger concurrency control (row locks per user) for concurrent settlement operators.
- Provider webhooks to transition `pending → completed/failed` asynchronously.
