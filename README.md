# Vinci Automation

Tutoring-operations automation: a colour-coded lesson **Schedule**, an admin
**Chatbot**, and the WhatsApp (WATI) automation that schedules classes, chases
tutors, takes their acceptances, assigns them, and sends out lesson materials.

- **Frontend** — React 19 + Vite (Vercel-ready) · `frontend/`
- **Backend** — FastAPI (Render-ready) · `backend/`
- **Database** — Supabase (Postgres) · `supabase/`
- **Messaging** — WATI (WhatsApp) · **LLM** — Ollama (free, local)

## Phase status

| Phase | Scope | State |
| ----- | ----- | ----- |
| **1.1** | Chatbot, backend+DB in prod, all WhatsApp working, automated triggers | ✅ built |
| **1.2** | Schedule hub — daily/weekly/monthly, 3-colour status | ✅ built |
| 2 | Lesson Dashboard | scaffolded (route + endpoints + preview) |
| 3 | Finances | scaffolded |
| 4 | Urgent News | scaffolded (live feed) |

## Architecture

```
React (Vercel)  ──HTTP──>  FastAPI (Render)  ──>  Supabase (Postgres)
   Schedule hub               REST + triggers          4 linked tables
   Chatbot                    WATI client      ──>  WATI  (WhatsApp)
                              Ollama client     ──>  Ollama (LLM)
   WATI webhook  ──POST──>  /api/webhooks/wati
```

Lessons live in Supabase (the source of truth). The automated triggers
(reminders, re-blast, tutor selection, file-send, cancellation) are a port of
the original Google Apps Scripts — see `backend/reference/README.md`.

## Quick start (local)

### 1. Supabase
1. Create a project at supabase.com.
2. SQL Editor → run `supabase/migrations/0001_phase1_schema.sql`, then
   `0002_seed_airtable.sql` (the real Airtable data — schools, teachers,
   courses, lessons — auto-generated from the exported CSVs).
3. Project Settings → API: copy the URL, the **anon** key, and the
   **service_role** key.

### 2. Backend
```bash
cd backend
.venv\Scripts\activate            # Windows (venv already created)
pip install -r requirements.txt
# .env is pre-filled with WATI/Airtable values from your materials.
# Add SUPABASE_URL + SUPABASE_KEY (service_role), then:
uvicorn app.main:app --reload
```
API: http://localhost:8000 · docs: http://localhost:8000/docs · health: `/api/health`

### 3. Frontend
```bash
cd frontend
npm install
# frontend/.env already points VITE_API_BASE_URL at http://localhost:8000
npm run dev
```
App: http://localhost:5173

### 4. Ollama (chatbot LLM, optional)
```bash
# install from ollama.com, then:
ollama pull llama3.1
```
The chatbot answers DB questions (unassigned, urgent, today, summary) and
exports Excel even without Ollama; Ollama only adds free-form replies.

## Testing Phase 1.1 (WhatsApp automation)

1. Backend + Supabase running, demo data loaded.
2. **Schedule** → click an unassigned (red/yellow) lesson → **Send WhatsApp
   blast**. Tutors with no number fall back to the two test numbers.
3. Tutor replies **"Accept"** → set the WATI webhook to
   `POST https://<backend>/api/webhooks/wati?token=<WATI_WEBHOOK_SECRET>`
   (use ngrok locally). The acceptance appears under the lesson's "Accepted tutors".
4. Click **Assign** on an accepted tutor → status flips to assigned (green) and
   the confirmation + **material link** is sent.
5. Tutor replies **"cancel"/"reschedule"** → lesson unassigns, admin is
   notified, the pool is re-blasted.

See `backend/.env.example` for every setting.

## Deploy

**Backend → Heroku** (the app lives in `backend/`). Heroku auto-detects
`backend/requirements.txt` + `backend/Procfile`; `backend/.python-version`
pins Python 3.11 and `backend/app.json` documents config vars + the Scheduler
add-on. No app is created until you run these:

```bash
heroku create vinci-automation-api
heroku stack:set heroku-24 -a vinci-automation-api
# secrets (config vars = the equivalent of your gitignored .env):
heroku config:set -a vinci-automation-api SUPABASE_URL=... SUPABASE_KEY=... \
  WATI_API_URL=... WATI_ACCESS_TOKEN=... WATI_WEBHOOK_SECRET=change-me \
  CORS_ORIGINS=https://your-app.vercel.app APP_URL=https://vinci-automation-api.herokuapp.com
# deploy the backend/ subtree (commits required):
git subtree push --prefix backend heroku main
```
(Monorepo alternative: `heroku-buildpack-monorepo` with `APP_BASE=backend`, then `git push heroku main`.)

**Reminder sweep** — Heroku Scheduler (`heroku addons:open scheduler`), hourly:
```bash
curl -fsS -X POST "$APP_URL/api/scheduling/run-due-reminders?token=$WATI_WEBHOOK_SECRET"
```

**Frontend → Vercel** (`frontend/vercel.json`). Set `VITE_API_BASE_URL` to the
Heroku URL as a Vercel env var. After deploy, repoint the WATI webhook to
`https://vinci-automation-api.herokuapp.com/api/webhooks/wati?token=<secret>`.

> `render.yaml` is kept as an inert alternative (Render). It doesn't affect Heroku — delete it if you don't want it.

## Project layout

```
vinci_automation/
├── frontend/   React app — features/{schedule,chatbot,lessonDashboard,finances,urgentNews}; vercel.json
├── backend/    FastAPI — app/{api/routes,services,schemas,core}; Procfile, app.json, .python-version
├── supabase/   migrations/ (schema + seed)
├── render.yaml (optional, inert)
└── README.md
```
