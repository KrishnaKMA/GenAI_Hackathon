# ClaimShield

ClaimShield is an AI-assisted insurance fraud detection platform that scores claims, builds entity graphs, explains suspicious patterns, and produces investigator-ready reports. It is designed around the idea that coordinated fraud rings are easier to catch when claims are analyzed as connected networks instead of isolated records.

## Demo / Preview

Primary demo flow:
- log in as an adjuster or admin
- review the dashboard and seeded claims
- open a suspicious claim report
- inspect the entity graph, graph evidence, SHAP-style feature contributions, and narrative
- submit a new claim and watch the backend score and classify it

Demo credentials:
- `admin / admin123`
- `adjuster1 / pass123`
- `investigator1 / pass123`

Local URLs:
- frontend: `http://localhost:5173`
- backend docs: `http://localhost:8000/docs`
- backend health: `http://localhost:8000/health`

Hosted path:
- Render deployment is configured through [`render.yaml`](./render.yaml)

## Why This Exists

Insurance fraud often shows up as repeated relationships between claimants, providers, and repair shops. Traditional per-claim review misses those connections. ClaimShield was built to surface those network patterns, combine them with tabular anomaly signals, and present the result in a way an investigator can actually use.

## Features

- JWT-based login flow for demo users and adjuster-style access
- claim intake flow with claimant, provider, repair shop, amount, and timing fields
- graph construction around claim entities and shared relationships
- graph-based fraud scoring using a GraphSAGE-style model
- tabular anomaly scoring using the saved anomaly artifact bundle
- combined fraud score and risk classification
- graph evidence and SHAP-style feature contribution output
- narrative case summary for investigators
- dashboard, claims list, report view, and dark-mode UI
- fallback local factsheets and IBM integration hooks
- local demo seeding and smoke-test scripts

## Tech Stack

Frontend:
- React
- TypeScript
- Vite
- Axios
- Cytoscape
- Recharts

Backend:
- FastAPI
- Uvicorn
- Pydantic
- PyJWT
- bcrypt
- cryptography

ML / Data:
- PyTorch
- torch-geometric
- scikit-learn
- SHAP
- LightGBM
- NumPy
- pandas

Infra / Deployment:
- Docker Compose for local demo mode
- SQLite for the default local and hosted path
- optional local Db2 path
- Render blueprint for hosted frontend + backend deployment

Optional IBM layer:
- watsonx.ai
- watsonx.governance
- Db2

## Project Structure

```text
frontend/                 React client
backend/                  FastAPI app
backend/api/routes/       API route handlers
backend/core/             database and security helpers
backend/services/         claim, graph, ML, IBM, reporting services
backend/models/           runtime model artifacts
models/                   training-side artifacts and notebooks
scripts/                  bootstrap, smoke, and demo seeding scripts
data/                     local runtime data
docker-compose.yml        local stack
render.yaml               Render deployment blueprint
```

Important files:
- [`backend/main.py`](./backend/main.py): FastAPI entrypoint and CORS setup
- [`backend/core/database.py`](./backend/core/database.py): SQLite / Db2 abstraction
- [`backend/services/ml_interface.py`](./backend/services/ml_interface.py): live ML inference path
- [`backend/services/ibm_interface.py`](./backend/services/ibm_interface.py): IBM integration plus fallback behavior
- [`frontend/src/lib/api.ts`](./frontend/src/lib/api.ts): frontend API client and cache invalidation
- [`scripts/bootstrap-local-db2.ps1`](./scripts/bootstrap-local-db2.ps1): local stack startup
- [`scripts/smoke-e2e.ps1`](./scripts/smoke-e2e.ps1): smoke test runner
- [`scripts/demo-matrix.ps1`](./scripts/demo-matrix.ps1): 24-case demo dataset generator

## How It Works

End-to-end workflow:

1. A user logs in and submits a claim.
2. The backend tokenizes and stores the claim entities.
3. Entity links are created between claimant, provider, and repair shop.
4. The graph model and tabular anomaly model run on the live claim context.
5. The backend produces:
   - `gnn_score`
   - `isolation_score`
   - `combined_score`
   - `risk_level`
6. Evidence is returned as graph relationships plus top feature contributions.
7. The frontend renders the investigator report.
8. If IBM credentials are present, the IBM layer can add hosted narrative and governance behavior. If not, the app falls back locally instead of failing.

## Setup and Installation

### Prerequisites

Recommended:
- Docker Desktop
- Node.js 20+
- npm 10+
- Python 3.11
- PowerShell on Windows

### Local Setup

1. Clone the repo.
2. Create `backend/.env` from [`backend/.env.example`](./backend/.env.example).
3. Fill in at least:
   - `FERNET_KEY`
   - `JWT_SECRET` or the RSA key pair fields
4. Start Docker Desktop.
5. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local-db2.ps1
```

This starts:
- backend
- frontend
- SQLite-backed demo mode by default

If you specifically want local Db2 too:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local-db2.ps1 -UseDb2
```

### Manual Local Commands

Docker Compose:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs backend --tail=200
```

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

Note:
- the checked-in local `venv` is not reliable on every machine
- Docker is the supported full-stack path for local verification

## Usage

Once the stack is running:

1. Open the frontend.
2. Log in with one of the demo users.
3. Review the dashboard and claims list.
4. Open a seeded suspicious claim such as a high-risk or critical case.
5. Inspect:
   - Entity Graph
   - GNN Evidence
   - SHAP Features
   - Narrative
6. Submit a new claim to trigger the full intake -> graph -> ML -> report flow.

For the controlled seeded demo dataset:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\demo-matrix.ps1 -ResetData
```

## Architecture

### Frontend

- React SPA for login, dashboard, claims, claim submission, and case reports
- calls the backend over HTTP using the API client in `frontend/src/lib/api.ts`
- uses short-lived caching and invalidation to keep the UI responsive

### Backend

- FastAPI service for auth, claim ingestion, graph construction, analysis, and reporting
- stores operational data in SQLite by default
- supports Db2 when explicitly configured

### ML Layer

- GraphSAGE-style model scores suspicious network structure
- saved tabular anomaly artifact scores claim-level anomalies
- backend combines both into a single risk result and explanation payload

### IBM Layer

- IBM integration is present in code
- live IBM behavior is credential-gated
- for hosted demo deployment, the recommended setting is `FORCE_MOCK_IBM=true`

## Results / Current Status

Working locally:
- frontend build
- backend API path
- login flow
- claim submission
- graph construction
- ML scoring path
- report rendering
- demo seeding and smoke test scripts

Current deployment stance:
- local demo: Docker Compose + SQLite
- hosted demo: Render backend + Render static frontend + persistent SQLite disk

Credential-gated pieces:
- live watsonx.ai narrative generation
- live watsonx.governance factsheets
- hosted IBM Cloud Db2

## Deployment

### Render

The repo includes [`render.yaml`](./render.yaml) for a two-part hosted setup:

- `claimshield-api` as a Render web service
- `claimshield-web` as a Render static site

Recommended Render configuration:
- backend uses `DB_BACKEND=sqlite`
- backend stores data at `/var/data/local.db`
- backend stores fallback factsheets at `/var/data/local_factsheets.json`
- `FORCE_MOCK_IBM=true`

Backend build / start:

```bash
pip install -r requirements-render.txt
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Frontend build:

```bash
npm install && npm run build
```

Frontend env:
- `VITE_API_HOST=<backend host>`

Backend env:
- `FRONTEND_URL=<frontend url>`
- `FERNET_KEY=<your key>`
- `JWT_SECRET=<your secret>` or RSA keys

## Verification

Frontend build:

```powershell
cd frontend
npm run build
```

Backend health:

```powershell
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Compress
```

Smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-e2e.ps1
```

## Challenges and Learnings

- integrating graph analysis, tabular anomaly scoring, and explainability into a single response path
- keeping the demo responsive enough for live use
- making the frontend feel consistent while backend analysis results update
- separating the local demo path from the hosted deployment path
- handling IBM integration as an optional layer rather than a hard dependency

## Future Improvements

- true live IBM activation once valid credentials are available
- cleaner hosted deployment verification on Render
- chunk splitting to reduce frontend bundle size
- stronger calibration of the tabular anomaly bridge
- richer graph exploration and filtering tools
- investigator feedback loops for model refinement

## Contributors

Built as a collaborative hackathon project across frontend, backend, ML, and IBM integration workstreams.

## License

No license file is currently included in this repository.

## Contact

If you are handing this repo to another developer, start with:
- [`backend/.env.example`](./backend/.env.example)
- [`scripts/bootstrap-local-db2.ps1`](./scripts/bootstrap-local-db2.ps1)
- [`render.yaml`](./render.yaml)
