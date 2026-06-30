"""DEPRECATED.

Authentication moved to Supabase Auth in Phase 1. Identity is owned by
Supabase Auth and roles by public.app_users (see app/api/routes/auth.py and
supabase/migrations/0005_phase1_auth.sql). This module is intentionally empty
and kept only to avoid stale imports. Do not add password/JWT logic here.
"""
