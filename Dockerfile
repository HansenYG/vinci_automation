# Vinci Automation Docker Setup
# Optimize backend performance with better dependency caching

# Multi-stage build for production backend
FROM python:3.11-slim AS backend
WORKDIR /app

# System dependencies for PostgreSQL binary operations
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies with better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY backend/app ./app
COPY backend/Procfile ./

# Database migrations
COPY backend/supabase/migrations ./supabase/migrations
COPY backend/scripts/create_users_table.py ./scripts/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check endpoint
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
