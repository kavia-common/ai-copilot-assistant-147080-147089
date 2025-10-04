# FastAPI Backend

This is the FastAPI backend for the AI Copilot.

## Optional: Supabase
Supabase is not required to run this backend. A stubbed client exists and will only be considered available if enabled and configured via environment variables.

To enable:
1. Copy `.env.example` to `.env`.
2. Set:
   - `ENABLE_SUPABASE=true`
   - `SUPABASE_URL=<your_supabase_url>`
   - Provide at least one key:
     - `SUPABASE_SERVICE_ROLE_KEY` (server-only, sensitive), or
     - `SUPABASE_ANON_KEY` (limited)
3. Optionally set `SUPABASE_JWT_SECRET` if you plan to use Supabase Auth.

If these variables are not set, the backend runs normally with Supabase disabled.

CORS origin can be configured with:
- `FRONTEND_ORIGIN` (default: `http://localhost:3000`)
