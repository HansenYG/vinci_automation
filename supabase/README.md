# Supabase

Database layer for Vinci Automation.

## Setup

1. Create a project at [supabase.com](https://supabase.com).
2. From **Project Settings → API**, copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → frontend `VITE_SUPABASE_ANON_KEY`
   - **service_role** key → backend `SUPABASE_KEY` (keep secret)
3. Paste these into `frontend/.env` and `backend/.env`.

## Migrations

SQL migration files live in `migrations/`. Apply them **in order**:

| File | Purpose |
| ---- | ------- |
| `0001_phase1_schema.sql` | Schema mirroring the 4 Airtable tables + offer pool + audit log, RLS, lookup/rollup views |
| `0002_seed_airtable.sql` | The real Airtable data (auto-generated from the exported CSVs) |
| `0003_max_tutors.sql` | Adds `max_tutors` column to courses for blast limits |
| `0004_lesson_income.sql` | Adds `lesson_income` column to lessons for financial tracking |
| `0005_phase1_auth.sql` | Auth schema: users table, admin role, RLS policies for Supabase Auth |

`0002` is generated from the exported CSVs by `backend/scripts/gen_seed_from_csv.py` —
re-run that script if the CSVs change.

Apply them either by:

- Pasting the SQL into the Supabase **SQL Editor** (run 0001 first, then 0002), or
- Using the [Supabase CLI](https://supabase.com/docs/guides/cli):

  ```bash
  supabase link --project-ref <your-project-ref>
  supabase db push
  ```

## Schema — mirrors the 4 Airtable tables

Natural keys match Airtable; **foreign keys are the anchor** for related data
(a lesson's teacher name/email/rate come live from the Teacher row via
`teacher_id`, never duplicated).

```
schools(school_id) ──< courses(course_id, school_id FK) ──< lessons(teacher_id FK, course_id FK)
                                                               │   + lesson_material_link (extra)
                                                               ├──< lesson_tutor_offers (pool / "Teacher's Accepted")
                                                               └──< lesson_events        (audit / Urgent News)
```

- **schools** — `school_id` PK, `school_name`, raw availability link fields.
- **teachers** — `teacher_id` PK ("TCH-001" / numeric), name, email, WhatsApp, rates, scores, CV, etc. (intrinsic columns only). **Sensitive — locked by RLS.**
- **courses** — `course_id` PK, `school_id` FK, topic, types, `revenue_per_lesson`.
- **lessons** — surrogate `id` + Airtable `lesson_id`, `teacher_id`/`course_id` FKs, status, role, duration, `tutor_assignment`, plus the design's extra **`lesson_material_link`**.
- **lesson_tutor_offers** — WhatsApp pool + 24h re-blast bookkeeping; "Teacher's Accepted" rows imported as `offer_status = 'accepted'`.
- **lesson_events** — append-only audit trail.

### Views (reproduce the Airtable lookups/rollups through the FKs)

- **`lessons_full`** — every `... (from Teacher)` / `... (from Course)` lookup + `lesson_payout`, resolved live via the FKs.
- **`teachers_full`** / **`courses_full`** / **`schools_full`** — intrinsic columns + rollups (lesson counts, hours, revenue, costs, profit margin, linked lists).
- **`lesson_schedule`** — stable feed for the Schedule UI: `within_a_week` + 3-colour status (green = assigned, red = unassigned ≤7 days, yellow = unassigned >7 days).
- **`urgent_news`** — lessons within a week that are unassigned or cancelled.

### Security

RLS is enabled on every table with **no anon policies**, so the public anon key cannot read tutor data. All Phase 1 access goes through the FastAPI backend using the **service_role** key. Introduce scoped policies when you add end-user auth in a later phase.
