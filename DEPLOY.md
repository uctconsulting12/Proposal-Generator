# Deploying JD Proposal Copilot (demo: local Ollama via ngrok)

Architecture for this demo:

```
Browser → [Render URL] → FastAPI backend (serves React + API)
                              ├── MongoDB Atlas        (all data: users, sessions, KB, logos)
                              └── ngrok URL → your PC's Ollama   (the LLM)
```

One cloud service serves both the React frontend and the API (same origin, so
no CORS setup needed). The LLM stays on your machine and is reached over ngrok.

---

## 1. Keep your machine serving the model

On your PC, leave these running for the whole demo:

```powershell
# Terminal 1 — Ollama listening on all interfaces
$env:OLLAMA_HOST = "0.0.0.0:11434"
$env:OLLAMA_ORIGINS = "*"
ollama serve

# Terminal 2 — tunnel (use a CLAIMED static domain so the URL is stable)
ngrok http 11434 --host-header="localhost:11434" --domain=YOURNAME.ngrok-free.app
```

Verify: `curl https://YOURNAME.ngrok-free.app/api/tags` returns your model list (HTTP 200).

> A free *dynamic* ngrok URL changes on every restart. Claim a free static
> domain in the ngrok dashboard (Domains) to avoid re-deploying each time.

---

## 2. Deploy the backend on Render (Docker)

1. Push this repo to GitHub.
2. Render → **New → Web Service** → connect the repo.
3. **Runtime: Docker** (it auto-detects the `Dockerfile`).
4. **Instance type: ≥ 1 GB RAM** (the embedding model OOMs on 512 MB).
5. Add the environment variables below.
6. Create. Render builds the image (frontend + backend) and starts it.

### Environment variables (set in Render → Environment)

| Key | Value |
|-----|-------|
| `COPILOT_LLM_PROVIDER` | `ollama` |
| `COPILOT_OLLAMA_URL` | `https://YOURNAME.ngrok-free.app/api/chat` |
| `COPILOT_MODEL_NAME` | `qwen3:14b` (or a smaller model for speed) |
| `COPILOT_MONGODB_URI` | your Atlas connection string |
| `COPILOT_MONGODB_DB_NAME` | `jd_copilot_auth` |
| `COPILOT_JWT_SECRET` | a real random secret (see below) |
| `COPILOT_LLM_TIMEOUT_S` | `300` (local model over a tunnel is slow) |

`COPILOT_SERVE_FRONTEND=true` and `COPILOT_HOST=0.0.0.0` are already baked into
the Dockerfile. Render injects `$PORT`; the container honors it.

Generate a JWT secret:
```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 3. Atlas network access

MongoDB Atlas → **Network Access** → add `0.0.0.0/0` (Render egress IPs are
dynamic). Security comes from the strong database-user password.

---

## 4. Verify

- `https://<render-url>/health` → `ollama_reachable: true` and `status: ok`.
  - If `ollama_reachable` is false → the ngrok URL is wrong/down or your PC is off.
- Open `https://<render-url>/` → sign up → upload a doc → start a proposal.
- Log out / back in (or another browser) → your data is still there (it's in Atlas).

---

## Build & run the image locally (optional sanity check)

```powershell
docker build -t proposal-copilot .
docker run --rm -p 8080:8080 `
  -e COPILOT_MONGODB_URI="<atlas-uri>" `
  -e COPILOT_OLLAMA_URL="https://YOURNAME.ngrok-free.app/api/chat" `
  -e COPILOT_JWT_SECRET="dev-secret" `
  proposal-copilot
# open http://localhost:8080/
```

---

## Notes / limits of this demo setup

- **Single worker only.** The vector index uses embedded Qdrant (one process).
  To scale to multiple instances later, move to Qdrant Cloud.
- **Your PC is a hard dependency.** If it sleeps, or Ollama/ngrok stop, the app
  can't generate proposals (everything else still works).
- **Speed.** A 14B model on CPU, over a home-upload tunnel, is slow. Use a
  smaller model (`llama3:8b`, `qwen2.5:3b`) for a snappier demo.
