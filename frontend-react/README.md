# ProposalPilot Frontend (React + Vite + MUI)

A standalone single-page application for the JD Proposal Copilot. It runs on
its own dev server (port `5173`) and talks to the FastAPI backend on
port `8082`.

## Stack

- React 18
- Vite 5 (dev server, HMR, production build)
- Material UI v6 (`@mui/material`, `@mui/icons-material`)
- Axios for HTTP
- React Router v6

## Directory layout

```
frontend-react/
├── index.html
├── vite.config.js          # dev server config + /api proxy to backend
├── package.json
├── public/
│   └── favicon.svg
└── src/
    ├── main.jsx            # entrypoint
    ├── App.jsx             # router
    ├── theme.js            # MUI theme (light + dark)
    ├── api/
    │   ├── client.js       # axios instance + JWT token store
    │   ├── auth.js
    │   ├── sessions.js
    │   └── kb.js
    ├── contexts/
    │   ├── AuthContext.jsx
    │   ├── SessionContext.jsx
    │   └── ThemeModeContext.jsx
    ├── components/
    │   ├── layout/
    │   │   ├── AppLayout.jsx
    │   │   ├── BrandMark.jsx
    │   │   ├── Sidebar.jsx
    │   │   └── Topbar.jsx
    │   ├── workspace/
    │   │   ├── ChatPanel.jsx
    │   │   ├── ProjectForm.jsx
    │   │   └── TechStackInput.jsx
    │   └── common/
    │       └── StatCard.jsx
    └── pages/
        ├── LoginPage.jsx
        ├── WorkspacePage.jsx
        ├── DashboardPage.jsx
        └── ClientDatabasePage.jsx
```

## Develop locally

From the repository root, run the backend and the frontend in two terminals:

```pwsh
# Terminal 1 — FastAPI backend on http://127.0.0.1:8082
python run.py --reload

# Terminal 2 — Vite dev server on http://127.0.0.1:5173
cd frontend-react
npm install     # first time only
npm run dev
```

Open <http://127.0.0.1:5173>. Vite proxies all `/api/*` requests to the
backend, so cookies/JWT and CORS work without extra configuration.

### Pointing at a different backend

Copy `.env.example` to `.env` and override `VITE_BACKEND_URL`:

```
VITE_BACKEND_URL=http://my-backend.local:8082
```

## Production build

```pwsh
cd frontend-react
npm run build     # emits frontend-react/dist
npm run preview   # serves dist on http://127.0.0.1:4173
```

To have the FastAPI process also serve the built bundle (single-port
deployment), set `COPILOT_SERVE_FRONTEND=true` before starting `run.py`. The
backend mounts `frontend-react/dist` at `/` when that flag is on.
