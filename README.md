# Vinci Automation

Tutoring-operations automation: a colour-coded lesson **Schedule**, an admin
**Chatbot**, an action-focused **Lesson Dashboard**, and WhatsApp (WATI)
automation that schedules classes, chases tutors, takes their acceptances,
assigns them, and sends out lesson materials.

- **Frontend** — React 19 + Vite deployed on **Vercel** (`main` branch) · `frontend/`
- **Backend** — FastAPI deployed on **Render** (`beta` branch) · `backend/`
- **Database** — Supabase (Postgres) · `supabase/`
- **Messaging** — WATI (WhatsApp)
- **LLM** — Ollama (local) or OpenAI-compatible providers (Groq, etc.)

## Production URLs

| Service | URL | Branch | Auto-deploy |
|---------|-----|--------|-------------|
| Frontend (prod) | https://vinci-automation.vercel.app | `production` | Vercel auto-deploy |
| Backend (prod)  | https://vinci-automation-api.onrender.com | `production` | Render auto-deploy |
| API Docs (prod) | https://vinci-automation-api.onrender.com/api/docs | — | — |
| Frontend (beta) | — | `beta` | Vercel (preview deploy) |
| Backend (beta)  | https://vinci-automation-api-beta.onrender.com | `beta` | Render auto-deploy |
| API Docs (beta) | https://vinci-automation-api-beta.onrender.com/api/docs | — | — |

<!-- SECURITY: Deploy hook URL/key removed. Rotate key in Render dashboard if it was exposed. -->

## Phase status

| Phase | Scope | State |
| ----- | ----- | ----- |
| **1.1** | Chatbot, backend+DB in prod, all WhatsApp working, automated triggers | ✅ built |
| **1.2** | Schedule hub — daily/weekly/monthly, 3-colour status | ✅ built |
| **2** | Lesson Dashboard — stat cards, filters, search, sorted table | ✅ built |
| **3** | Finances | 🏗 scaffolded |
| **4** | Urgent News | 🏗 scaffolded |

## Architecture

```
                    ┌────────────────────────────────────────┐
React (Vercel) ────>  FastAPI (Render) ────>  Supabase       │
  Schedule hub          REST + triggers        (Postgres)     │
  Chatbot / Dock       WATI client  ──────>  WATI (WhatsApp) │
  Lesson Dashboard     LLM client   ──────>  Ollama / Groq   │
  Auth (Supabase)                                           │
                    └────────────────────────────────────────┘
WATI webhook  ──POST──>  /api/webhooks/wati
```

Lessons live in Supabase (the source of truth). Automated triggers (reminders,
re-blast, tutor selection, file-send, cancellation) are a port of the original
Google Apps Scripts — see `backend/reference/README.md`.

## Auth

Uses Supabase Auth with email/password login. Session uses cookie-based
storage (@supabase/ssr) instead of localStorage to reduce JWT token
exfiltration risk. Role-gating is applied on the frontend (admin role required).

**Security note:** For full httpOnly cookie protection, implement a
token-exchange endpoint on the FastAPI backend.

**Test credentials:** `hansenyg@vinciai.academy` / `VinciBeta2026!`

## Quick start (local)

### 1. Supabase
1. Create a project at supabase.com.
2. SQL Editor → run `supabase/migrations/0001_phase1_schema.sql`, then
   `0002_seed_airtable.sql`, then `0003_max_tutors.sql`, then `0004_lesson_income.sql`.
3. Project Settings → API: copy the URL, the **anon** key, and the
   **service_role** key.

### 2. Backend
```bash
cd backend
.venv\Scripts\activate            # Windows (venv already created)
pip install -r requirements.txt
# .env is pre-filled with WATI values from your materials.
# Add SUPABASE_URL + SUPABASE_KEY (service_role) + JWT_SECRET_KEY + ADMIN_PASSWORD, then:
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

### 4. LLM (chatbot, optional)
```bash
# Ollama (local):
ollama pull llama3.1
# Or set LLM_PROVIDER=openai with LLM_API_KEY for Groq/OpenAI
```
The chatbot answers DB questions (unassigned, urgent, today, summary) and
exports Excel even without an LLM; the LLM only adds free-form replies.

## E2E Test Results

Latest test run (2 Jul 2026): **35/35 test cases passed, 0 failures.**
See `Vinci_Automation_E2E_Test_Report.md` for full details.

Coverage includes: auth (login/logout/session/role-gating), Schedule (calendar
views/stepping/zoom/chips/drawer), Lesson Dashboard (stats/filters/search/
sorting/buckets/empty-state), Assignment flows (accept/cancel/reschedule/
re-blast), Dock (open/close/chat/data tab/persistence), AI Chatbot
(confirmation flow for reschedule/create/delete).

## Deploy pipeline

### Branch strategy

| Branch | Environment | Hosting |
|--------|-------------|---------|
| `production` | 🟢 User testing / production | Vercel (prod) + Render (prod) |
| `beta` | 🟡 Dev testing / staging | Vercel (preview) + Render (beta) |

Workflow: commit → push to `beta` → test → merge `beta` → `production` to release.

### Frontend (Vercel)

| Environment | Branch | VITE_API_BASE_URL |
|-------------|--------|-------------------|
| Production | `production` | `https://vinci-automation-api.onrender.com` |
| Beta (preview) | `beta` | `https://vinci-automation-api-beta.onrender.com` |

Push to `production` branch — Vercel auto-deploys from `frontend/` with
`vercel.json`. Set `VITE_API_BASE_URL` as a Vercel environment variable per
the table above.

### Backend (Render)

| Environment | Branch | Blueprint |
|-------------|--------|-----------|
| Production | `production` | `render.yaml` |
| Beta | `beta` | `render.beta.yaml` |

Push to the branch — Render auto-deploys using the matching blueprint.
Env vars are set in the Render dashboard (never committed).

### Docker (local)
```bash
docker-compose up --build
```
Runs backend on :8000, frontend on :5173, and Ollama on :11434.

## Project layout

```
vinci_automation/
├── frontend/          React app — features/{schedule,chatbot,lessonDashboard,finances,urgentNews}; vercel.json
├── backend/           FastAPI — app/{api/routes,services,schemas,core}; Procfile
├── supabase/          migrations/ (schema + seed: 0001–0004)
├── render.yaml        Render blueprint (production, main branch)
├── render.beta.yaml   Render blueprint (beta, beta branch)
├── docker-compose.yml Local dev: backend + frontend + Ollama
├── Dockerfile         Docker build for backend
└── run-local.ps1      One-click local startup script
```

## Key backend modules

| Module | Purpose |
|--------|---------|
| `services/scheduling.py` | `blast_lesson()`, `handle_cancellation()`, `record_acceptance()`, `assign_tutor()` |
| `services/chatbot.py` | AI chatbot logic, system prompt, `answer()`, `execute_operation()` |
| `services/wati.py` | WATI WhatsApp client — `normalize_phone()`, `send_template_message()` |
| `services/repos.py` | DB helpers — `list_rows()`, `update_row()`, `delete_row()` |
| `services/auth.py` | JWT auth — `create_initial_admin_user()`, `authenticate_user()`, `create_access_token()` |
| `services/export.py` | Excel export for lessons, teachers, courses, schools |
| `api/routes/chat.py` | Chat endpoints including `POST /api/chat/execute` for confirmed actions |
| `core/config.py` | All settings — WATI, LLM, Supabase, business rules |
