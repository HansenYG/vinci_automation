# Vinci Automation

Full-stack application scaffold.

- **Frontend** — React (JavaScript) + Vite
- **Backend** — FastAPI
- **Database** — Supabase

> This is the development framework only. Application features are added on top of this structure.

## Project structure

```
vinci_automation/
├── frontend/                 # React + Vite app
│   ├── src/
│   │   ├── assets/
│   │   ├── components/       # Reusable UI components
│   │   ├── context/          # React context providers
│   │   ├── hooks/            # Custom hooks
│   │   ├── lib/
│   │   │   └── supabaseClient.js
│   │   ├── pages/            # Route-level views
│   │   ├── services/
│   │   │   └── api.js        # Axios client for the backend
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── .env.example
│
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── api/routes/       # API route modules
│   │   ├── core/             # Config + Supabase client
│   │   ├── models/           # Data models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic
│   │   └── main.py           # App entrypoint
│   ├── requirements.txt
│   └── .env.example
│
└── supabase/
    └── migrations/           # SQL migrations
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+
- A Supabase project (for database access)

## Getting started

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # then fill in your Supabase credentials

uvicorn app.main:app --reload
```

API runs at http://localhost:8000 (interactive docs at `/docs`).
Health check: http://localhost:8000/api/health

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env          # then fill in your values

npm run dev
```

App runs at http://localhost:5173.

### 3. Supabase

See [`supabase/README.md`](supabase/README.md) for creating the project and
wiring up credentials.

## Environment variables

**frontend/.env**

| Variable                  | Description                       |
| ------------------------- | --------------------------------- |
| `VITE_API_BASE_URL`       | Base URL of the FastAPI backend   |
| `VITE_SUPABASE_URL`       | Supabase project URL              |
| `VITE_SUPABASE_ANON_KEY`  | Supabase anon public key          |

**backend/.env**

| Variable        | Description                                  |
| --------------- | -------------------------------------------- |
| `CORS_ORIGINS`  | Comma-separated allowed frontend origins     |
| `SUPABASE_URL`  | Supabase project URL                         |
| `SUPABASE_KEY`  | Supabase service_role (or anon) key          |
