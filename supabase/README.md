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

SQL migration files live in `migrations/`. Apply them either by:

- Pasting the SQL into the Supabase **SQL Editor**, or
- Using the [Supabase CLI](https://supabase.com/docs/guides/cli):

  ```bash
  supabase link --project-ref <your-project-ref>
  supabase db push
  ```
