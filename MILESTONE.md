# FinChat Analytics Milestone Report

Generated on: 2026-06-13

## Executive Summary

FinChat Analytics is currently in a **local integrated prototype / pre-MVP integration milestone**.

The repository already contains the main product surfaces described in `PRODUCT_DESCRIPTION.md`: a FastAPI backend, a Streamlit frontend, MySQL-backed data ingestion, feature engineering, and runtime ML/analytics tools for CLV, churn, survival analysis, uplift, causal discovery, and text-to-SQL.

However, it is **not yet at the production MVP milestone** from `project_plan.md`, because several required platform pieces are still missing or stubbed: MLflow tracking/model registry, real authentication, Redis caching, Dockerization, tests, CI/CD, deployment, and production-grade KPI/upload handling.

## Current Milestone

Current status: **between Phase 5 and Phase 6, with unfinished work from Phases 2, 3, 4, 6, and 7**.

Evidence:

- Phase 0 and Phase 1 are mostly represented in the repo through project structure, sample data generation, MySQL schema, and ingestion scripts.
- Phase 2 is partially implemented through `pipeline/feature_engineering.py` and `pipeline/train_all_models.py`, but MLflow logging, model registry, validation, and automated training are not implemented.
- Phase 3 is not implemented. There is no MLflow server config, no `mlflow/` directory, no MLflow dependency in `requirements.txt`, and no `mlflow` imports in the codebase.
- Phase 4 is partially implemented. `backend/main.py`, `backend/agent.py`, `backend/tools/ml_tools.py`, and `backend/tools/text2sql.py` provide a working FastAPI backend and hybrid analytics agent, but authentication is missing and some endpoints return placeholder data.
- Phase 5 is partially implemented. `frontend/app.py` and `frontend/components.py` provide a Streamlit chat/dashboard/upload/export UI, but it is still a local tester-style frontend rather than a deployed production dashboard.
- Phase 6 is partially implemented through frontend-backend HTTP integration, but no pytest test suite or performance/edge-case tests are present.
- Phase 7 is not implemented. `docker-compose.yml` exists but is empty, and there are no Dockerfiles.

## Feature Status

| Area | Status | Notes |
|---|---:|---|
| Product definition | Present | `PRODUCT_DESCRIPTION.md` defines the target dashboard, assistant, offline ML, and online inference product. |
| Data schema | Present | `data/table_design.sql` defines MySQL tables for customers, transactions, and customer features. |
| Data ingestion | Partial | CSV-to-MySQL ingestion exists in `data/ingestion_pipeline.py`; upload endpoint is still a placeholder. |
| Feature engineering | Present | `pipeline/feature_engineering.py` computes RFM, rolling activity, behavior, promotion, conversion, churn, and duration features. |
| CLV model | Present, runtime-trained | Uses `lifetimes` BG/NBD and Gamma-Gamma in `pipeline/train_all_models.py`. |
| Survival model | Present, runtime-trained | Uses CoxPH in `pipeline/train_all_models.py`. |
| Churn model | Present, runtime-trained | Uses RandomForest in `pipeline/train_all_models.py`. |
| Uplift model | Present, runtime-trained | Uses a T-learner approach in `pipeline/train_all_models.py`. |
| Causal discovery | Present, runtime-trained | Uses DirectLiNGAM from `causal-learn`. |
| FastAPI backend | Present | `backend/main.py` exposes `/health`, `/api/chat`, `/api/kpis`, and `/api/upload`. |
| Agent routing | Present | `backend/agent.py` has rule-based plus Gemini-assisted routing. |
| Text-to-SQL | Present | `backend/tools/text2sql.py` generates read-only SQL and blocks mutating statements. |
| Frontend | Present | Streamlit app exists in `frontend/app.py` with chat, KPI sidebar, upload, charts, and report export. |
| Tests | Minimal/missing | Only `data/test_db_connection.py` exists; no real unit/integration test suite. |
| Docker | Missing | `docker-compose.yml` is empty and no Dockerfiles are present. |
| CI/CD | Missing | No GitHub Actions workflows are present in the visible repo. |
| Deployment | Planned only | `Deployment_Plan.md` describes AWS deployment but no deploy config exists. |

## Supabase, Auth, Redis, MLflow, and Frontend Check

| Capability | Present? | Finding |
|---|---:|---|
| Supabase database | No | The app uses MySQL via SQLAlchemy and PyMySQL. There is no Supabase client dependency or Supabase database integration in application code. |
| Supabase Auth | No | No Supabase Auth integration, JWT verification, session handling, RLS policy setup, or frontend auth flow is implemented. |
| Supabase MCP config | Config only | `.mcp.json` points to the Supabase MCP server in read-only mode, but this is agent tooling configuration, not product runtime integration. |
| General backend auth | No | `project_plan.md` lists JWT + API key auth as incomplete, and `backend/main.py` has no auth dependencies or middleware. |
| Redis caching | Dependency only | `requirements.txt` includes `redis` and `aiocache`, but no Redis connection, cache decorator, cache reads/writes, or cache invalidation logic appears in the codebase. |
| MLflow | Planned only | Docs mention MLflow, but `requirements.txt` does not include `mlflow`, there are no MLflow imports, no tracking server config, no registry code, and no model promotion flow. |
| Frontend | Yes, partial | `frontend/app.py` and `frontend/components.py` implement a Streamlit frontend connected to the FastAPI backend, but it is not production-deployed and uses placeholder KPI/upload behavior. |

## Important Gaps

1. **Models are trained at request time.**
   The backend calls functions in `pipeline/train_all_models.py` directly through `MLToolService`. This means CLV, churn, survival, uplift, and causal discovery are recomputed during user requests instead of loading versioned production models.

2. **MLflow is not wired.**
   The product plan expects experiment tracking, artifact logging, model registry, validation, and production model loading. None of that exists yet.

3. **Authentication is absent.**
   `/api/chat`, `/api/kpis`, and `/api/upload` are publicly callable in local form. `tenant_id` is accepted as plain request input, not enforced by verified identity.

4. **Redis caching is not implemented.**
   There is no query/result cache around text-to-SQL, KPI results, feature engineering, LLM responses, or ML tool outputs.

5. **KPI and upload endpoints are placeholders.**
   `/api/kpis` returns random values. `/api/upload` returns a fake processed row count and does not run ingestion.

6. **The frontend exists but is still prototype-grade.**
   It supports chat, charts, upload UI, KPI display, prompt shortcuts, health check, and report export, but relies on backend stubs and local configuration.

7. **Operational readiness is missing.**
   No Dockerfiles, no populated compose file, no CI/CD workflows, no health checks beyond `/health`, and no automated test coverage are present.

## Recommended Next Steps

### 1. Stabilize the Local MVP

- Replace random `/api/kpis` values with real aggregate queries from MySQL.
- Make `/api/upload` call the ingestion pipeline safely, validate CSV schema, and return real ingestion results.
- Add focused pytest coverage for backend endpoints, SQL sanitization, feature engineering, and ML tool routing.
- Add error handling for missing database credentials and unavailable LLM/model dependencies.

### 2. Add MLflow Properly

- Add `mlflow` to `requirements.txt`.
- Create an MLflow tracking setup for local development.
- Update training code to log params, metrics, artifacts, and model signatures.
- Register CLV, churn, survival, uplift, and causal models in MLflow.
- Change backend inference to load registered production models instead of training models during each request.

### 3. Add Authentication and Tenant Safety

- Decide between Supabase Auth or custom JWT/API key auth.
- If using Supabase Auth, add Supabase client/server configuration, verify JWTs in FastAPI, and map authenticated users to tenants.
- Enforce tenant filtering server-side instead of trusting request-provided `tenant_id`.
- Add authorization tests for cross-tenant access.

### 4. Add Redis Caching

- Add Redis connection settings to `.env.example` and backend config.
- Cache expensive outputs: KPI aggregates, schema introspection, text-to-SQL results, feature frames, and ML inference results.
- Add cache keys that include tenant, query/model version, and input parameters.
- Add invalidation after data upload or retraining.

### 5. Dockerize and Prepare Deployment

- Add backend and frontend Dockerfiles.
- Populate `docker-compose.yml` with backend, frontend, MySQL, Redis, and optionally MLflow.
- Add container health checks.
- Keep secrets out of images and use environment variables.

### 6. Move Toward Production MVP

- Add GitHub Actions for linting, testing, Docker build, and scheduled training.
- Add performance testing for common chatbot queries.
- Complete documentation for local setup, retraining, auth, deployment, and model registry usage.
- Then proceed to AWS/Supabase deployment architecture depending on the chosen database/auth direction.

## Bottom Line

The project has a solid local prototype: backend, frontend, data schema, feature engineering, and analytics tools are all present. The current milestone is best described as **pre-production MVP integration**.

It does **not** yet have Supabase runtime integration, Supabase Auth, Redis caching, or MLflow. It **does** have a Streamlit frontend, but the frontend and backend still depend on placeholder endpoints and request-time model computation.
