# =====================================================================
# run-local.ps1 — start the whole Vinci Automation stack locally.
# Standard ports: backend http://localhost:8000, frontend http://localhost:5173.
#
# One-time prerequisites (already installed on this machine):
#   - Docker Desktop (running)        - Supabase CLI
#   - Node.js + npm                   - Ollama (+ `ollama pull llama3.2`)
#   - backend\.venv created with deps (pip install -r backend\requirements.txt)
#
# Usage:  right-click > Run with PowerShell, or:  ./run-local.ps1
# Stop:   close the two app windows, then run `supabase stop` for the DB.
# =====================================================================

$root = $PSScriptRoot
Write-Host "== Vinci Automation : local stack ==" -ForegroundColor Cyan

# 1) Database — local Supabase (Docker). Idempotent; first run applies the
#    migrations (schema + Airtable seed). Data persists across stop/start.
Write-Host "`n[1/4] Starting Supabase (Docker)..." -ForegroundColor Yellow
supabase start

# 2) LLM — Ollama runs as a Windows background service; confirm the model.
Write-Host "`n[2/4] Checking Ollama model..." -ForegroundColor Yellow
try { ollama list } catch { Write-Warning "Ollama not reachable - the chatbot will use its offline fallback." }

# 3) Make sure the frontend targets the standard backend port (8000).
$envLocal = Join-Path $root 'frontend\.env.local'
if (Test-Path $envLocal) { Remove-Item $envLocal -Force; Write-Host "Removed frontend\.env.local (old 8001 override)" }

# 4) Launch backend + frontend, each in its own window.
Write-Host "`n[3/4] Backend  -> http://localhost:8000  (API docs: /docs)" -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

Write-Host "[4/4] Frontend -> http://localhost:5173" -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$root\frontend'; npm run dev"

Write-Host "`nTwo windows are starting up. Open http://localhost:5173 in your browser." -ForegroundColor Green
Write-Host "(If 8000/5173 are busy from an earlier run, close those windows or reboot first.)" -ForegroundColor DarkGray
