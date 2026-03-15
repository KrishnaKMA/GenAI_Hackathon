# ClaimShield

ClaimShield is a fraud analysis application for insurance claims. It combines:
- a React frontend for claim intake, dashboards, graph visualization, and investigator reports
- a FastAPI backend for auth, claim ingestion, graph building, orchestration, and reporting
- a live ML scoring path using a graph model and a tabular anomaly model
- IBM integration hooks for narrative generation, governance factsheets, and Db2

This repository is set up for local development and local demo use first. The recommended runtime is Docker Compose.
The local demo stack uses SQLite by default for responsiveness, with local Db2 still available when you explicitly want to test that path.

## What The System Does

End-to-end flow:

1. A user logs in and submits a claim in the frontend.
2. The backend tokenizes the claim entities and stores the claim.
3. Related graph edges are created between claimant, provider, and repair shop entities.
4. The ML layer runs:
   - GraphSAGE-style graph scoring for network fraud patterns
   - a tabular anomaly model for claim-level risk patterns
5. The backend combines those results into a fraud score and risk level.
6. Explanations are generated from graph evidence and top contributing tabular features.
7. The IBM layer can add:
   - Granite narrative generation
   - governance factsheet logging
   - hosted Db2 support
8. The frontend renders the combined report for the investigator.

## Current State

Working locally now:
- frontend
- backend API
- auth and JWT login flow
- claim submission
- graph building
- ML scoring path
- fast local demo backend on SQLite
- dashboard, claims table, report view, dark theme
- smoke tests for core scenarios

Still dependent on external credentials:
- live watsonx.ai narrative generation
- live watsonx.governance factsheets
- hosted IBM Cloud Db2

If IBM credentials are missing or placeholder-level, the app stays usable locally and falls back to local narrative/factsheet behavior instead of failing.

## Repository Layout

Top-level structure:

```text
frontend/                  React application
backend/                   FastAPI application
models/                    trained model artifacts and notebooks
scripts/                   local startup and smoke-test scripts
data/                      local runtime data
docker-compose.yml         local stack
```

Important backend files:
- `backend/main.py`: FastAPI entrypoint
- `backend/core/database.py`: SQLite and Db2 abstraction
- `backend/core/security.py`: JWT, password hashing, tokenization helpers
- `backend/services/claim_ingestor.py`: claim ingestion and entity tokenization
- `backend/services/graph_builder.py`: graph relationships and graph helpers
- `backend/services/ml_interface.py`: live ML scoring path
- `backend/services/ibm_interface.py`: IBM integration and fallback logic
- `backend/services/report_generator.py`: report assembly
- `backend/api/routes/`: API route handlers

Important frontend files:
- `frontend/src/App.tsx`: app routing and layout
- `frontend/src/lib/api.ts`: API client and frontend-side caching
- `frontend/src/pages/`: page-level UI
- `frontend/src/components/`: reusable UI components

## Prerequisites

Recommended:
- Docker Desktop
- Node.js 20+
- npm 10+
- Python 3.11
- PowerShell on Windows

You can run the project without Docker for parts of development, but the supported full local stack is Docker Compose because it includes the backend runtime dependencies and optional local Db2 support.

## Dependencies

Frontend runtime dependencies:
- React 18
- React Router
- Axios
- Cytoscape
- Recharts
- react-hot-toast

Frontend build dependencies:
- Vite
- TypeScript
- `@vitejs/plugin-react`

Backend runtime dependencies:
- FastAPI
- Uvicorn
- Pydantic
- PyJWT
- bcrypt
- pyotp
- cryptography
- httpx
- python-dotenv

ML dependencies:
- torch
- torch-geometric
- scikit-learn
- shap
- numpy
- pandas
- lightgbm

IBM dependencies:
- ibm-db
- ibm-watsonx-ai
- ibm-aigov-facts-client

For exact pinned versions, see:
- [backend/requirements.txt](C:\Users\alihu\Projects\FraudTracker\GenAI_Hackathon\backend\requirements.txt)
- [frontend/package.json](C:\Users\alihu\Projects\FraudTracker\GenAI_Hackathon\frontend\package.json)

## Environment Variables

Local environment values are loaded from `backend/.env`.

That file is intentionally ignored by git. Use:
- [backend/.env.example](C:\Users\alihu\Projects\FraudTracker\GenAI_Hackathon\backend\.env.example)

Important variables:

### Security
- `JWT_PRIVATE_KEY`
- `JWT_PUBLIC_KEY`
- `JWT_SECRET`
- `FERNET_KEY`

### Frontend / API
- `FRONTEND_URL`

### IBM
- `WATSONX_API_KEY`
- `WATSONX_PROJECT_ID`
- `WATSONX_SPACE_ID`
- `WATSONX_URL`
- `DB2_DSN`

### Local database runtime
- `DB_BACKEND`
- `DB_CONNECT_RETRIES`
- `DB_CONNECT_DELAY_SECONDS`
- `DB2_DATABASE`

Notes:
- `WATSONX_API_KEY` must be a real IBM Cloud IAM API key to activate live IBM calls.
- The placeholder value `claimshield-api` is not sufficient.
- If `DB2_DSN` is not set for hosted IBM Cloud Db2, the local Docker Db2 path can still be used.

## Model Artifacts

The backend expects the trained artifacts at:
- `backend/models/gnn/pretrained/weights.pt`
- `backend/models/anomaly/iforest.pkl`

The repo also contains top-level copies under `models/`.

The runtime currently loads the saved graph checkpoint and the saved tabular bundle and applies them to live claim data through the integration logic in [backend/services/ml_interface.py](C:\Users\alihu\Projects\FraudTracker\GenAI_Hackathon\backend\services\ml_interface.py).

## Recommended Local Run

Use the bootstrap script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local-db2.ps1
```

What it does:
- starts backend and frontend in fast local demo mode
- uses SQLite by default
- does not require Db2 for the normal demo path

If you specifically want local Db2 too:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local-db2.ps1 -UseDb2
```

That mode:
- starts the local Db2 container
- waits for Db2 readiness
- creates `CLAIMDB` if needed
- then starts backend and frontend

URLs:
- Frontend: [http://localhost:5173](http://localhost:5173)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: [http://localhost:8000/health](http://localhost:8000/health)

Demo credentials:
- `admin / admin123`
- `adjuster1 / pass123`
- `investigator1 / pass123`

## Manual Docker Commands

Start the full stack:

```powershell
docker compose up --build -d
```

Check running containers:

```powershell
docker compose ps
```

Check backend health:

```powershell
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Compress
```

Check backend logs:

```powershell
docker compose logs backend --tail=200
```

## Running Without Docker

This is possible for partial development, but not recommended for the full stack.

Frontend only:

```powershell
cd frontend
npm install
npm run dev
```

Backend only:

```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Limitations of non-Docker local runs:
- no local Db2 container unless you provision it separately
- heavier manual dependency management
- IBM SDK and ML runtime setup is more fragile outside the container path

## API Overview

Main routes:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/login` | login |
| `GET` | `/claims` | list claims |
| `POST` | `/claims` | submit claim |
| `GET` | `/claims/{claim_token}` | get one claim |
| `POST` | `/analyze/{claim_token}` | run full analysis |
| `GET` | `/analyze/{claim_token}/cached` | get cached inference log row |
| `POST` | `/analyze/demo/{risk_level}` | load demo scenario |
| `GET` | `/factsheets` | retrieve governance-style factsheets |
| `GET` | `/admin/stats` | dashboard stats |

The interactive schema is available at:
- [http://localhost:8000/docs](http://localhost:8000/docs)

## Frontend Notes

The frontend is built as a single-page React application.

Key behaviors:
- auth token stored in local storage
- claims, factsheets, and stats requests are cached briefly on the client to reduce duplicate loads
- the report page reuses cached reports when possible to avoid re-running analysis unnecessarily
- the UI is styled for dark mode by default

## ML Notes

The ML layer is live in the current local stack.

What it does:
- loads the saved graph model
- loads the saved tabular model
- builds graph and tabular features from live claim/entity data
- computes:
  - `gnn_score`
  - `isolation_score`
  - `combined_score`
  - `risk_level`
- returns graph evidence and top feature contributions

Smoke-tested scenario ordering:
- clean property claim -> low
- high-value auto repair claim -> high
- repeat claimant with stronger pattern reuse -> critical
- medical claim without repair-shop pattern -> low

## IBM Notes

IBM integration code is present and wired into the backend.

When valid credentials are available, the intended behavior is:
- generate narrative through watsonx.ai
- log and read factsheets through watsonx.governance
- use hosted Db2 if configured

Without valid IBM credentials:
- narrative falls back locally
- factsheets fall back to `data/local_factsheets.json`
- local Docker Db2 remains the primary database path

## Verification

Backend unit tests:

```powershell
docker compose exec backend python -m unittest discover -s tests -v
```

End-to-end smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-e2e.ps1
```

That smoke script covers:
- login
- claim creation
- analysis
- score validation
- graph payload presence

## Troubleshooting

### Frontend looks slow or keeps reloading lists

Check:
- backend health is OK
- frontend container was rebuilt after code changes
- backend logs are not showing repeated auth failures

Useful commands:

```powershell
docker compose ps
docker compose logs backend --tail=200
```

### IBM stays in mock mode

This usually means one of these is true:
- `WATSONX_API_KEY` is missing
- `WATSONX_API_KEY` is still placeholder-level
- IBM SDK initialization failed

You need a real IBM Cloud IAM API key.

### Db2 startup is slow

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local-db2.ps1
```

That handles local initialization more reliably than manually starting each service one by one.

### Windows local Vite build throws `EPERM`

That is a local Windows process restriction issue. The Docker frontend build is the reliable verification path in this repo.

## If You Are Handing This Repo To Someone Else

Tell them this:

1. Use Docker Compose, not ad hoc local runs, for the full stack.
2. Start with the bootstrap script.
3. Use the demo credentials above.
4. The ML path is already integrated.
5. The IBM path is integrated in code, but real IBM activation still needs the actual API key and any hosted Db2 credentials.
