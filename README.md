# ClaimShield

ClaimShield is an end-to-end insurance fraud workflow built with a React frontend, a FastAPI backend, a live ML scoring path, and IBM integration hooks for narrative generation, governance, and Db2 storage.

## Current Status

What is working now:
- Frontend is running and integrated with the backend.
- Backend API is running with auth, claim submission, analysis, reports, factsheets, and agent endpoints.
- ML analysis is live.
  - GraphSAGE weights are loaded from `backend/models/gnn/pretrained/weights.pt`.
  - The tabular model is loaded from `backend/models/anomaly/iforest.pkl`.
  - Claims go through graph building, ML scoring, explanation generation, and report assembly.
- Local Db2 is wired through Docker and used by the backend.

What still needs real credentials:
- IBM watsonx.ai live narrative generation
- IBM watsonx.governance live factsheets
- IBM Cloud Db2 DSN if you want hosted Db2 instead of the local Docker Db2 instance

Right now the IBM layer is integrated in code, but it stays in fallback mode until a real IBM Cloud IAM API key is provided.

## Architecture

End-to-end flow:

1. User submits a claim in the frontend.
2. Backend tokenizes and stores claim and entity data.
3. Graph relationships are built for claimant, provider, and repair shop entities.
4. ML layer runs:
   - GraphSAGE for graph/network fraud signals
   - tabular anomaly model for claim-level risk signals
5. Explanations are generated from graph evidence and tabular feature contributions.
6. IBM layer can add:
   - Granite narrative generation
   - governance factsheet logging
   - hosted Db2 connectivity
7. Frontend shows the final combined result.

## Local Run

Recommended local startup:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-local-db2.ps1
```

That script:
- starts the local Db2 container
- creates `CLAIMDB` if needed
- starts backend and frontend

App URLs:
- Frontend: [http://localhost:5173](http://localhost:5173)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Demo login:
- `admin / admin123`

## Docker Commands

Manual startup if needed:

```powershell
docker compose up --build -d
```

Useful checks:

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Compress
docker compose logs backend --tail=200
```

## Environment

Local secrets live in `backend/.env`. That file is ignored by git.

Important variables:
- `JWT_PRIVATE_KEY`
- `JWT_PUBLIC_KEY`
- `FERNET_KEY`
- `FRONTEND_URL`
- `WATSONX_API_KEY`
- `WATSONX_PROJECT_ID`
- `WATSONX_SPACE_ID`
- `WATSONX_URL`
- `DB2_DSN`

Current IBM requirement:
- `WATSONX_API_KEY` must be a real IBM Cloud IAM API key.
- The placeholder value `claimshield-api` is not enough to activate live IBM calls.

If the IBM credentials are missing or placeholder-level:
- Granite narrative falls back to local mock output
- governance factsheets fall back to `data/local_factsheets.json`

## Verification

Backend health:

```powershell
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Compress
```

Backend tests:

```powershell
docker compose exec backend python -m unittest discover -s tests -v
```

End-to-end smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-e2e.ps1
```

Scenarios covered in the smoke run:
- clean property claim
- high-value auto repair claim
- repeat high-risk claimant
- medical claim without a repair shop

## Repo Layout

Key areas:
- `frontend/`
  - React app and dark-themed UI
- `backend/`
  - FastAPI app, DB layer, auth, ML, IBM integration
- `backend/services/ml_interface.py`
  - live ML scoring path
- `backend/services/ibm_interface.py`
  - IBM integration and fallback behavior
- `backend/core/database.py`
  - Db2 and SQLite abstraction
- `scripts/bootstrap-local-db2.ps1`
  - local startup helper
- `scripts/smoke-e2e.ps1`
  - end-to-end smoke test

## Presentation Notes

For the current local demo:
- frontend works
- backend works
- ML scoring works
- local Db2 works
- IBM code path is present, but real IBM activation still needs the actual IAM API key

That means the product is demoable end to end locally today, with IBM switching from fallback to live as soon as valid credentials are added.
