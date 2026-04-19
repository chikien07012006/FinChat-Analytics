

```markdown
# FinChat Analytics – Full Production Project Plan

**Project**: FinChat Analytics – AI-Powered Customer Retention Assistant  
**Objective**: Build a standalone B2B web application with a natural language chatbot that helps banks, fintech startups, and SMEs analyze and predict customer behavior for RFM segmentation, Churn Prediction, CLV, Survival Analysis, Uplift Modeling, and Causal Discovery.  
**Tech Stack**: Python, FastAPI, Streamlit, LangChain Agent, MLflow, MySQL, Plotly, Docker, AWS  
**Approach**: Offline Training Pipeline + Online Inference 

**Total Estimated Duration**: 6–8 weeks 
  ```
---

## Phase 0: Project Initialization (1 day)

- [x] Create a new private GitHub repository and invite the team
- [x] Initialize the project folder structure:
  ```bash
  finchat-analytics/
  ├── pipeline/          # Offline training pipeline
  ├── backend/           # FastAPI + LangChain Agent
  ├── frontend/          # Streamlit UI
  ├── mlflow/            # MLflow server configuration
  ├── data/
  ├── .github/workflows/
  ├── docker-compose.yml
  └── requirements.txt
  ```
- [x] Set up local development environment (Python 3.12)
- [x] Create `.env.example` and `.gitignore` files
- [x] Configure branch protection rules on `main` branch (require PR reviews)

---

## Phase 1: Data Preparation (2–3 days)

- [x] Generate or import suitable sample banking data using `generate_bank_data.py`
- [x] Design MySQL database schema (`raw_transactions`, `customer_data`, `customer_features`)
- [x] Migrate data from SQLite to MySQL
- [x] Build data ingestion pipeline (CSV → raw tables)
- [x] Create data quality checks (missing values, outliers, duplicates)

---

## Phase 2: Feature Engineering & Offline Training Pipeline (7–8 days)

- [x] Implement `pipeline/feature_engineering.py` (RFM, spending_last_30d/90d, frequency_last_*, tenure features, etc.)
- [ ] Build `pipeline/train_all_models.py`:
  - Run feature engineering and save to `customer_features` table
  - Train all models: CLV (BG/NBD + Gamma-Gamma), Survival (CoxPH), Churn Classification, Uplift Modeling, Causal Discovery
  - Wrap models using `mlflow.pyfunc` where necessary
- [ ] Log all experiments, parameters, metrics, and artifacts to MLflow
- [ ] Register trained models in MLflow Model Registry (Staging → Production)
- [ ] Implement model validation logic before promoting to Production
- [ ] Create GitHub Actions workflow for automated daily training (`train_models.yml`)

---

## Phase 3: MLflow Setup (2 days)

- [ ] Set up MLflow Tracking Server (local first, then remote on AWS)
- [ ] Configure MLflow with PostgreSQL backend store and S3 artifact store
- [ ] Enable Model Registry and stage transition workflow
- [ ] Implement functions to load Production models from MLflow in the backend

---

## Phase 4: Backend Development – FastAPI + LangChain Agent (5–6 days)

- [ ] Build FastAPI application (`backend/main.py`)
- [ ] Create LangChain Agent with custom tools and proper routing
- [ ] Develop 5 online inference tools (load model from MLflow + SQL query only):
  - CLV Tool
  - Survival Analysis Tool
  - Churn Classification Tool
  - Uplift Modeling Tool
  - Causal Discovery Tool
- [ ] Add error handling, structured logging, and rate limiting
- [ ] Implement JWT + API key authentication
- [ ] Define Pydantic request/response schemas

---

## Phase 5: Frontend Development – Streamlit (4–5 days)

- [ ] Build the main Streamlit application (`frontend/app.py`):
  - Natural language chat interface
  - Dashboard sidebar with key KPIs (churn rate, avg CLV, segment distribution)
  - Transaction data upload functionality
  - Interactive Plotly charts
  - Report export (HTML/PDF)
- [ ] Add chat history and conversation saving
- [ ] Implement dark/light mode and responsive design

---

## Phase 6: Integration & End-to-End Testing (3–4 days)

- [ ] Connect Streamlit frontend with FastAPI backend
- [ ] Test LangChain Agent multi-tool routing
- [ ] Write unit tests and integration tests (pytest)
- [ ] Perform performance testing (target latency < 2 seconds for complex queries)
- [ ] Test edge cases (empty data, Vietnamese/English queries, model failures)

---

## Phase 7: Dockerization (2 days)

- [ ] Create Dockerfiles for backend, frontend, and MLflow
- [ ] Write `docker-compose.yml` for local development and production
- [ ] Use multi-stage builds to optimize image size
- [ ] Add health checks and restart policies

---

## Phase 8: CI/CD with GitHub Actions (2 days)

- [ ] Create `ci.yml` workflow (linting, testing, Docker build)
- [ ] Create `cd.yml` workflow (build and push images to AWS ECR on merge to main)
- [ ] Configure existing `train_models.yml` workflow
- [ ] Set up GitHub Secrets (AWS credentials, database connection, OpenAI key, MLflow URI)

---

## Phase 9: Deployment on AWS (4–5 days)

- [ ] Deploy MySQL database using Amazon RDS
- [ ] Deploy MLflow server (EC2 or ECS + S3 + PostgreSQL)
- [ ] Deploy FastAPI backend on ECS / Fargate
- [ ] Deploy Streamlit frontend on ECS or a simple PaaS
- [ ] Set up Application Load Balancer (ALB), Route 53 domain, and HTTPS
- [ ] Configure S3 for model artifacts and generated reports
- [ ] Enable auto-scaling and CloudWatch logging

---


## Phase 10: Documentation & Handover (2 days)

- [ ] Write comprehensive README.md (local run, deployment, model retraining)
- [ ] Generate API documentation (Swagger)
- [ ] Document MLflow usage and experiment tracking
- [ ] Create user guide for business users
- [ ] Document how to retrain models and update data

---

## Milestones & Go-Live Criteria

- [ ] MVP completed (chatbot can successfully answer all 5 advanced queries)
- [ ] All models registered and served from MLflow Production stage
- [ ] Application successfully deployed on AWS with custom domain
- [ ] CI/CD pipelines are green and fully automated
- [ ] Average response latency under 2 seconds
- [ ] Security measures and backups are in place


---