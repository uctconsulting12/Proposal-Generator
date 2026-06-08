<div align="center">

<img src="frontend-react/public/favicon.svg" width="92" alt="ProposalPilot AI logo" />

# ProposalPilot AI

**An AI proposal copilot that turns job descriptions into client-ready, branded PDF proposals — grounded in *your* past work.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![Material UI](https://img.shields.io/badge/MUI-v6-007FFF?logo=mui&logoColor=white)](https://mui.com/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)

</div>

---

## What it does

ProposalPilot AI is a **freelancer / agency proposal copilot**. You paste a job description, it pulls in the most relevant excerpts from *your own* past proposals via RAG, runs a guided chat that produces a draft, lets you iterate on it, and exports a fully branded PDF in the template of your choice.

It runs **fully on your own infrastructure** — local Ollama or Gemini for the LLM, local Qdrant for the vector store, local MongoDB for accounts, your own logo / colours / templates for branding.

---

## Demo

<div align="center">

### Dashboard — track every proposal and its outcome
<img src="Demo%20Image/Dashboard.png" alt="Dashboard view" width="900" />

### Active Workspace — guided intake + live chat with rendered markdown
<img src="Demo%20Image/Active%20proposal.png" alt="Active proposal workspace" width="900" />

### Company Profile — brand your output (logo, accent, signature, template)
<img src="Demo%20Image/Company%20profile.png" alt="Company profile" width="900" />

</div>

> A full walkthrough video is included in the repo as [`DEMO Video.mp4`](DEMO%20Video.mp4).

---

## Use cases — problems this solves

| Pain point | How ProposalPilot AI fixes it |
|---|---|
| **Proposals take hours and read generic** | Guided chat enforces a 7-section technical structure (Executive Summary → Architecture → Timeline → Why Us) so every output reads like a senior engineer wrote it. |
| **You forget which past projects to cite** | Drop past work into the Client Database — the RAG layer surfaces the most relevant excerpts on every new proposal and the AI cites them by name. |
| **Different clients need different "feels"** | 4 built-in PDF templates (Modern, Classic, Bold, Technical) — pick a default per company and override per proposal. |
| **Branding has to be re-applied every time** | Set logo + brand accent + signature once on the Profile page; every PDF picks them up automatically. |
| **No central place to see what won/lost** | Dashboard tracks Total / Finalized / Drafts / Won counters and lets you mark outcomes per proposal. |
| **You want to send formal RFP responses** | The "Technical Brief" template matches enterprise RFP layout — numbered sections, sub-sections, navy tables, centred-rule cover. |
| **Sensitive client data must stay on-prem** | Backend talks to local Ollama and local Qdrant by default. No proposal text or KB content ever leaves the host unless you configure it to. |

---

## Architecture

Two services run on separate ports — clean dev loop, simple production deploy.

```
┌──────────────────────────────────────────┐    ┌──────────────────────────────────────────┐
│  Frontend (Vite + React 18 + MUI v6)     │    │  Backend  (FastAPI + Python 3.11+)       │
│  http://127.0.0.1:5173                   │◄──►│  http://127.0.0.1:8082                   │
│                                          │    │                                          │
│  • Pages: Workspace / Dashboard /        │    │  • /api/auth      JWT signup / signin    │
│    Client DB / Company Profile           │    │  • /api/session   start / message /      │
│  • react-markdown + remark-gfm           │    │    finalize / proposal.pdf               │
│  • Material UI theme (light + dark)      │    │  • /api/kb        upload / list / index  │
│                                          │    │  • /api/profile   profile + logo         │
│                                          │    │  • /api/templates 4 PDF templates        │
└──────────────────────────────────────────┘    └──────────────────────────────────────────┘
                                                                  │
                  ┌───────────────────────────────────────────────┼────────────────────────────────────┐
                  ▼                       ▼                       ▼                                    ▼
            ┌──────────┐           ┌──────────┐           ┌──────────────┐                ┌──────────────────┐
            │  Ollama  │           │  Qdrant  │           │  MongoDB     │                │  fpdf2 templates │
            │  (LLM)   │           │  (RAG)   │           │  (users +    │                │  modern / classic│
            │  qwen3   │           │  fastembed│          │  profiles)   │                │  bold / technical│
            └──────────┘           └──────────┘           └──────────────┘                └──────────────────┘
```

---

## Quick setup

### Prerequisites

- **Python 3.11+**
- **Node 18+** (for the React frontend)
- **[Ollama](https://ollama.com/)** running locally with a model pulled — or a Gemini API key
  ```pwsh
  ollama pull qwen3:14b
  ```
- **MongoDB** running locally (used for user accounts + company profiles)
  - Default: `mongodb://localhost:27017`

### 1. Backend

```pwsh
# from repo root
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# config — defaults work for local dev
copy .env.example .env

# start FastAPI on http://127.0.0.1:8082
.\venv\Scripts\python.exe run.py --reload
```

### 2. Frontend

```pwsh
cd frontend-react
npm install        # first time only
npm run dev        # starts Vite on http://127.0.0.1:5173
```

The Vite dev server proxies `/api/*` to the backend, so cookies / JWT / CORS just work.

### 3. Open

[http://127.0.0.1:5173](http://127.0.0.1:5173) — sign up (your first account is created automatically), then jump to **Company Profile** to upload your logo and pick a template before starting your first proposal.

> **Production single-port deploy:** `npm run build` (in `frontend-react/`) → set `COPILOT_SERVE_FRONTEND=true` → run `uvicorn app.main:app`. The FastAPI process will then serve the built React bundle at `/` alongside the API.

---

## How to use it (end-to-end)

1. **Set up your brand** — open **Company Profile** → upload logo, write a short company intro (used by the AI for voice + on the PDF cover), pick a brand colour, pick a default PDF template.
2. **Seed past projects** *(optional but high-leverage)* — open **Client Database** → upload past proposals / project docs (`.pdf`, `.docx`, `.txt`, `.md`, `.json`). Each gets an AI summary and is indexed into the RAG store.
3. **Start a proposal** — on **Workspace**, fill the project intake (title, JD, budget, timeline, tech stack) → **Start Session**.
4. **Iterate in chat** — the assistant produces a short draft, you review the rendered markdown live in the chat, type changes or `approve` to generate the full proposal.
5. **Export** — click **Export PDF** to use your default template, or open the dropdown to render the same proposal in any other template.
6. **Finalize** — locks the session against new drafts but keeps it open for **Q&A** about the proposal contents.
7. **Track outcome** — on **Dashboard**, mark each proposal **Won / Lost / Pending**.

---

## PDF templates

| Template | Best for | Look |
|---|---|---|
| **Modern Teal** | SaaS, agencies, tech proposals | Accent band cover, sans-serif body, accent headings |
| **Classic Serif** | Enterprise, legal, government | Times serif, minimal accent, centred cover with hairline rules |
| **Bold Statement** | Pitch-deck style proposals | Full-bleed accent cover, oversized title, numbered sections |
| **Technical Brief** | Formal RFP responses, consulting | Numbered sub-sections (1, 1.1), navy table headers, centred-rule cover |

All templates pick up your logo, brand colour, company intro and signature from the Company Profile.

---

## API surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/signup` · `/api/auth/signin` | Email/password auth → returns JWT |
| `GET`  | `/api/auth/me` | Verify token |
| `POST` | `/api/session/start` | Begin a proposal session from a JD intake |
| `POST` | `/api/session/{id}/message` | Chat turn (questioning / draft / final / Q&A) |
| `POST` | `/api/session/{id}/finalize` | Lock session — Q&A still works |
| `GET`  | `/api/session/{id}/proposal.pdf?template=...` | Export PDF (optional per-export template override) |
| `GET`  | `/api/session/list` · `/api/session/{id}` | List / load past sessions |
| `GET`  | `/api/profile` · `PUT /api/profile` | Read / update company profile |
| `POST` | `/api/profile/logo` · `DELETE /api/profile/logo` · `GET /api/profile/logo` | Manage company logo |
| `GET`  | `/api/templates` | List available PDF templates |
| `POST` | `/api/kb/upload` · `/api/kb/list` · `/api/kb/reindex` | Manage the past-projects knowledge base |
| `GET`  | `/health` | Liveness + dependency reachability |

Interactive Swagger UI: `http://127.0.0.1:8082/docs`. All errors return `{"error": "...", "detail": ...}` with an `X-Request-ID` header for log correlation.

---

## Project layout

```
Chatbot_RAG_Agent/
├── app/                              FastAPI backend
│   ├── main.py                       app factory, lifespan, middleware
│   ├── config.py                     typed settings (COPILOT_* env vars)
│   ├── prompts.py                    system prompt + stage instructions
│   ├── llm.py                        Ollama / Gemini client
│   ├── rag.py                        Qdrant + fastembed
│   ├── pdf.py                        thin facade over template registry
│   ├── pdf_templates/                modern / classic / bold / technical
│   ├── profiles.py                   per-user company profile (Mongo + disk logo)
│   ├── auth.py                       MongoDB users + JWT
│   ├── storage.py                    thread-safe JSON session store
│   ├── services.py                   DI container
│   └── routers/                      auth · sessions · kb · profile · templates · health
├── frontend-react/                   Vite + React 18 + MUI v6 SPA
│   ├── src/api/                      axios client + per-domain modules
│   ├── src/contexts/                 Auth / Session / Profile / ThemeMode
│   ├── src/components/               layout / workspace / templates / common
│   └── src/pages/                    Login · Workspace · Dashboard · ClientDB · Profile
├── knowledge_base/                   client uploads (one folder per user)
├── profiles/                         company logos (one folder per user)
├── qdrant_data/                      local vector index
├── Demo Image/                       README screenshots
├── tests/                            pytest suite
├── run.py                            backend entrypoint
└── requirements.txt
```

---

## Configuration

`.env` (prefix `COPILOT_`) — defaults work out of the box for local dev:

| Setting | Default | Purpose |
|---|---|---|
| `COPILOT_HOST` / `COPILOT_PORT` | `127.0.0.1` / `8082` | Backend bind address |
| `COPILOT_LLM_PROVIDER` | `ollama` | `ollama` or `gemini` |
| `COPILOT_MODEL_NAME` | `qwen3:14b` | LLM model id (per provider) |
| `COPILOT_GEMINI_API_KEY` | _(blank)_ | Required if provider = `gemini` |
| `COPILOT_MONGODB_URI` | `mongodb://localhost:27017` | Used for users + profiles |
| `COPILOT_JWT_SECRET` | `change-me-in-env` | **Change in production** |
| `COPILOT_CORS_ORIGINS` | `5173`, `4173` | Whitelist for the React dev / preview server |
| `COPILOT_SERVE_FRONTEND` | `false` | Set `true` to serve the built React bundle from FastAPI |
| `COPILOT_ENABLE_QUESTIONS` | `false` | Ask clarifying questions before drafting |

---

## Tests

```pwsh
.\venv\Scripts\python.exe -m pytest
```

---

## Tech stack

**Backend** — FastAPI · Pydantic v2 · Uvicorn · httpx · MongoDB (PyMongo) · JWT (PyJWT) · Qdrant + fastembed (RAG) · fpdf2 (PDF rendering) · Ollama / Google Gemini

**Frontend** — React 18 · Vite 5 · Material UI v6 · React Router v6 · Axios · react-markdown + remark-gfm

---

## License

Internal / proprietary. Contact the maintainer for usage outside this organisation.
