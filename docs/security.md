# Security Recommendations

LLM-COUNSEL is a **reference implementation**. It ships with no authentication,
no rate limiting, no encryption at rest, and no audit logging. This document
enumerates what you need to add before any non-local deployment.

## Current Security Posture

| Concern | Default | Risk |
|---|---|---|
| Authentication | None | Anyone who can reach the API can run deliberations on your OpenRouter account |
| Network binding | `127.0.0.1` (safe default) | If `API_HOST=0.0.0.0`, the open API is exposed on any accessible interface |
| Rate limiting | None | A loop against `/api/matters/{id}/message` can rack up arbitrary OpenRouter charges |
| Encryption at rest | None | Matter JSON files are plaintext on disk |
| Secrets handling | `.env` file | API key is plaintext on disk; not integrated with any secrets manager |
| Audit logging | None | No record of who did what |
| Input validation | Pydantic type + length bounds | No content filtering, no PII scrubbing, no prompt-injection defenses |
| CORS | `localhost:5173` only | Hardcoded; will block any non-local frontend |
| Transport | HTTP | No TLS; anyone on the network can see matter content and API keys |

## Minimum Changes Before Production

### 1. Authentication

Add at least token-based auth on every `/api/*` route.

```python
from fastapi import Depends, Header, HTTPException

async def verify_token(authorization: str = Header(...)) -> None:
    expected = os.getenv("LLMCOUNSEL_API_TOKEN")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    if authorization[7:] != expected:
        raise HTTPException(403, "Invalid token")

@app.get("/api/matters", dependencies=[Depends(verify_token)])
async def list_matters():
    ...
```

For multi-user, move to JWT or OAuth (GitHub, Google, or your IdP).

### 2. Rate Limiting

The deliberation endpoint is the expensive one (9 model calls per request).
Rate-limit it separately from the cheap CRUD endpoints.

Recommended: `slowapi` (FastAPI integration for `limits`).

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/matters/{matter_id}/message")
@limiter.limit("10/hour")  # aggressive; tune to your budget
async def send_message(...):
    ...
```

### 3. Secrets Manager

Remove `OPENROUTER_API_KEY` from `.env` and load it from a real secrets
manager: AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, or 1Password
CLI for development.

### 4. Encryption at Rest

For matter JSON files containing sensitive legal questions, either:

- **Move to a managed database** (Postgres with `pgcrypto` column encryption, or
  a managed service with encryption at rest), or
- **Keep the JSON store but encrypt individual matter files** with an
  envelope-encryption scheme (data keys per matter, master key in the secrets
  manager).

The `backend/storage.py` module is small enough that swapping its implementation
is straightforward.

### 5. Audit Logging

Log every matter read/write and every deliberation call with:

- Authenticated user ID (once auth is added)
- Matter ID
- Operation (`create | get | delete | send_message`)
- Timestamp (UTC, ISO 8601)
- Outcome (success, HTTP status code, model errors)

Ship logs to a centralized, append-only store outside the application host.

### 6. Input Validation Beyond Pydantic

Pydantic enforces types and length bounds. You may additionally want:

- **PII scrubbing** — strip SSNs, credit cards, medical record numbers before
  sending to third-party models
- **Prompt injection hardening** — treat user-provided `context` as untrusted
  and surround it with clear delimiters in the prompt
- **Content policy** — block categories of questions your organization
  prohibits

### 7. CORS

Replace the hardcoded `http://localhost:5173` list with an environment-driven
allowlist.

### 8. TLS Everywhere

Terminate TLS at a reverse proxy (nginx, Caddy, Cloudflare). Never run the
uvicorn process on a public port without TLS in front of it.

### 9. Monitoring and Alerting

The deliberation path makes 9 LLM calls per question. You need:

- Alerts on per-hour cost exceeding a threshold
- Alerts on 502/500 rate spikes
- A dashboard showing per-model success rates, latency, and error modes
  (rate limited vs timeout vs malformed response)

## Cost Containment

Independent of security, consider adding:

- **Per-user daily budgets** enforced before calling `run_full_counsel`
- **Per-matter cost tracking** computed from OpenRouter usage headers in each
  response
- **Model downgrade fallbacks** — if Opus 4.6 is rate-limited, fall back to a
  cheaper Anthropic model rather than failing the deliberation

## Attorney-Client Privilege

**This system does not create or preserve attorney-client privilege.** Questions
submitted to LLM-COUNSEL are transmitted to third-party model providers via
OpenRouter. Treat all inputs as discoverable. This is a legal research tool,
not a substitute for privileged communication with a licensed attorney.
