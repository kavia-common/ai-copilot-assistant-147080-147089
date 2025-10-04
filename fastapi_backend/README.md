# FastAPI Backend

This is the FastAPI backend for the AI Copilot.

The backend never exposes secrets to the frontend. Any API keys (e.g., OpenAI,
Supabase service role) must only be set in the backend environment.

The backend never exposes secrets to the frontend. Any API keys (e.g., OpenAI,
Supabase service role) must only be set in the backend environment.

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

## Optional: OpenAI-powered replies
The chat endpoint can optionally use OpenAI Chat Completions.

To enable:
1. Copy `.env.example` to `.env`.
2. Set:
   - `OPENAI_API_KEY=<your_openai_key>` (server-side only; do NOT expose to frontend)
   - Optionally set `OPENAI_MODEL` (default: `gpt-4o-mini`)

Behavior:
- When `OPENAI_API_KEY` is set, the backend will call OpenAI non-streaming and return the model’s reply.
- On any error or if the key is missing, the backend falls back to a deterministic reply without external calls.
- A 10s timeout is applied to the OpenAI request, and errors are handled gracefully.

## Optional: OpenAI-powered replies
The chat endpoint can optionally use OpenAI Chat Completions.

To enable:
1. Copy `.env.example` to `.env`.
2. Set:
   - `OPENAI_API_KEY=<your_openai_key>` (server-side only; do NOT expose to frontend)
   - Optionally set `OPENAI_MODEL` (default: `gpt-4o-mini`)

Behavior:
- When `OPENAI_API_KEY` is set, the backend will call OpenAI non-streaming and return the model’s reply.
- On any error or if the key is missing, the backend falls back to a deterministic reply without external calls.
- A 10s timeout is applied to the OpenAI request, and errors are handled gracefully.
