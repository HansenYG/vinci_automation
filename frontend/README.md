# Vinci Automation — Frontend

React 19 + Vite application deployed on Vercel.

## Features

- **Schedule** — Month/Week/Day calendar view with colour-coded lesson chips
- **Lesson Dashboard** — Stat cards, filters (status/course/tutor/date/search), sortable table
- **Chatbot / Dock** — AI admin assistant with preset buttons, chat history, and Data tab (quick lesson creation + Excel export)
- **Finances** (scaffolded)
- **Urgent News** (scaffolded)
- **Auth** — Supabase Auth with session persistence, role-gating

## Key files

| File | Purpose |
|------|---------|
| `src/features/schedule/SchedulePage.jsx` | Schedule calendar with views, zoom, chips |
| `src/features/lessonDashboard/LessonDashboardPage.jsx` | Lesson dashboard with stats, filters, table |
| `src/features/chatbot/ChatPanel.jsx` | AI chatbot UI with confirmation buttons |
| `src/features/chatbot/ChatDock.jsx` | Dock panel (Chat + Data tabs) |
| `src/features/chatbot/dockContext.js` | Dock state (open/closed) |
| `src/services/endpoints.js` | API wrappers |
| `src/services/api.js` | Axios instance with auth interceptor |

## Environment

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server (Vite) |
| `npm run build` | Production build |
| `npm run lint` | ESLint |
