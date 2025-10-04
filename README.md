# ai-copilot-assistant-147080-147089

## Optional: Supabase (Backend)
Supabase is not required to run this project. The backend includes a stubbed client that is only initialized if enabled via environment variables.

To enable:
1. Copy `fastapi_backend/.env.example` to `fastapi_backend/.env`.
2. Set `ENABLE_SUPABASE=true`.
3. Provide `SUPABASE_URL` and at least one key:
   - `SUPABASE_SERVICE_ROLE_KEY` (server-only, sensitive), or
   - `SUPABASE_ANON_KEY` (limited permissions).
4. Optionally set `SUPABASE_JWT_SECRET` if you plan to use Supabase Auth.

If these variables are not set, the backend runs normally and Supabase features remain disabled.

## Optional: Supabase (Backend)
Supabase is not required to run this project. The backend includes a stubbed client that is only initialized if enabled via environment variables.

To enable:
1. Copy `fastapi_backend/.env.example` to `fastapi_backend/.env`.
2. Set `ENABLE_SUPABASE=true`.
3. Provide `SUPABASE_URL` and at least one key:
   - `SUPABASE_SERVICE_ROLE_KEY` (server-only, sensitive), or
   - `SUPABASE_ANON_KEY` (limited permissions).
4. Optionally set `SUPABASE_JWT_SECRET` if you plan to use Supabase Auth.

If these variables are not set, the backend runs normally and Supabase features remain disabled.