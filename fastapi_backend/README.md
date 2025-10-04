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

Behavior and time budgets:
- When `OPENAI_API_KEY` is set, the backend will call OpenAI non-streaming and return the model’s reply.
- A strict inner OpenAI segment budget of ~12s is enforced with one quick retry and per-request httpx timeout.
- The route `/api/chat` has a hard 13s overall timeout and will either return a reply or a structured timeout error within SLA.
- On any error or if the key is missing, the backend falls back to a deterministic reply; on timeout, a friendly message is returned.
- Errors return a structured JSON with `error.code`, `message`, and timing metadata.

## Minimal request shape and examples

The POST /api/chat endpoint accepts a minimal JSON body:

```
POST /api/chat
Content-Type: application/json

{
  "message": "What is water?"
}
```

Example response:
```
{
  "reply": "Water is H₂O, a molecule made of two hydrogen atoms and one oxygen atom. It's essential for life."
}
```

The endpoint also supports a richer shape:
```
{
  "messages": [
    {"role": "user", "content": "Give me examples of vegetables"}
  ],
  "response_style": "list" // optional: 'plain' | 'list' | 'guided'
}
```

### Minimal React fetch example

```js
async function ask(question) {
  const res = await fetch(`${process.env.REACT_APP_BACKEND_URL || "http://localhost:3001"}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: question }),
  });
  if (!res.ok) {
    // Handle errors (e.g., 400/502/504) by showing a friendly message
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `Request failed with ${res.status}`);
  }
  const data = await res.json();
  return data.reply;
}
```

Note: If you need conversation history or styling hints, send the richer messages[] format shown above.

## Minimal request shape and examples

The POST /api/chat endpoint accepts a minimal JSON body:

```
POST /api/chat
Content-Type: application/json

{
  "message": "What is water?"
}
```

Example response:
```
{
  "reply": "Water is H₂O, a molecule made of two hydrogen atoms and one oxygen atom. It's essential for life."
}
```

The endpoint also supports a richer shape:
```
{
  "messages": [
    {"role": "user", "content": "Give me examples of vegetables"}
  ],
  "response_style": "list" // optional: 'plain' | 'list' | 'guided'
}
```

### Minimal React fetch example

```js
async function ask(question) {
  const res = await fetch(`${process.env.REACT_APP_BACKEND_URL || "http://localhost:3001"}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: question }),
  });
  if (!res.ok) {
    // Handle errors (e.g., 400/502/504) by showing a friendly message
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `Request failed with ${res.status}`);
  }
  const data = await res.json();
  return data.reply;
}
```

Note: If you need conversation history or styling hints, send the richer messages[] format shown above.
