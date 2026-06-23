# Reference — legacy Google Apps Scripts

The Phase-1 backend is a port of four production Google Apps Scripts that drove
the original WATI ↔ Google Sheets ↔ Airtable automation. The scripts are the
behavioural source of truth; this file maps each one to its new home.

The original `.js` files are kept locally under `reference/legacy/` (gitignored,
because they contain live WATI / Airtable secrets). They also live in
`Downloads/Vinci Automation Prompt Materials/`.

| Legacy script | What it did | Ported to |
| ------------- | ----------- | --------- |
| `calendar to sheet.js` | Scan calendar for `[UNASSIGNED]`, blast the tutor pool, 24h re-blast | `app/services/scheduling.py` → `blast_lesson()`, `run_due_reminders()` + `app/services/wati.py` |
| `reply handling.js` | Inbound webhook: tutor "Accept" → flip status, link teacher | `app/api/routes/webhooks.py` (accept branch) → `scheduling.record_acceptance()` |
| `tutor confirmation .js` | Scan `[ASSIGNED]`, send confirmation + **material link**, assign teacher | `app/services/scheduling.py` → `assign_tutor()` + `wati.send_confirmation()` |
| `cancellation or rescheduling handling.js` | Inbound webhook: cancel/reschedule → unassign, notify admin, re-blast | `app/api/routes/webhooks.py` (cancel branch) → `scheduling.handle_cancellation()` |

## What changed in the port

- **Source of truth:** Google Calendar + Sheets → **Supabase** (4 linked tables).
  "Unassigned lessons" is now a DB query, not a calendar scan.
- **State:** the Sheet's `Status` / `Last Send Result` / `Last Blast Sent`
  columns → the `lesson_tutor_offers` table; the Airtable links → `lessons`.
- **Secrets:** the hardcoded WATI token / Airtable PAT → backend `.env`
  (gitignored). Nothing secret is committed.
- **WATI:** standardised on `/api/v1/sendTemplateMessages`; same templates and
  parameter names, so the approved WATI templates work unchanged.
