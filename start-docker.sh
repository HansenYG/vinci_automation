# Vinci Automation Startup Script
# Docker-based development setup

#!/usr/bin/env bash
set -e

echo "============================================"
echo "Vinci Automation - Docker Startup"
echo "============================================"

echo ""
echo "1. Setting up environment variables..."

# Check if .env exists, create from example if not
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo ""
        echo "⚠️  IMPORTANT: Please edit .env file and set your required variables:"
        echo "   - SUPABASE_URL"
        echo "   - SUPABASE_KEY (service_role)"
        echo "   - WATI_API_URL"
        echo "   - WATI_ACCESS_TOKEN"
        echo "   - ADMIN_PASSWORD"
        echo "   - JWT_SECRET_KEY (generate a secure key)"
        echo ""
    else
        echo "ERROR: .env.example not found!"
        echo "Please create a .env file with the required environment variables."
        exit 1
    fi
fi

echo ""
echo "2. Starting Docker containers..."

echo ""
echo "Starting services:"
echo "   - Backend API: http://localhost:8000"
echo "   - Frontend: http://localhost:5173"
echo "   - Ollama LLM: http://localhost:11434"
echo "   - Supabase DB: http://localhost:5432"
echo ""

echo "Backend API docs: http://localhost:8000/docs"
echo "Frontend app: http://localhost:5173"
echo ""

echo "Health check endpoints available:"
echo "   - Backend: http://localhost:8000/api/health"
echo "   - Auth: http://localhost:8000/api/auth/me"
echo ""

echo "============================================"
chmod +x $0
