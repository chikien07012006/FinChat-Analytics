# FinChat Analytics — AI-Powered Customer Retention Platform

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MLflow](https://img.shields.io/badge/MLflow-2.16+-0194E2.svg)](https://mlflow.org/)

**FinChat Analytics** is a high-performance B2B analytics platform designed for banks, fintech startups, and SMEs. It leverages advanced causal discovery and predictive modeling to provide actionable insights into customer behavior, retention, and lifetime value through a natural language interface.

---

## 🚀 Key Capabilities

-   **🧠 Causal Discovery**: Identify direct drivers of churn using `DirectLiNGAM` structural causal modeling.
-   **⏳ Survival Analysis**: Predict precisely *when* a customer will churn using Cox Proportional Hazards models.
-   **💎 CLV Estimation**: Calculate Customer Lifetime Value using BG/NBD and Gamma-Gamma probabilistic models.
-   **📈 Uplift Modeling**: Quantify the incremental impact of marketing promotions (T-Learner approach).
-   **🤖 AI Agent**: A LangChain-powered assistant that translates natural language queries into complex data insights.

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph "Data Layer"
        GD[Data Generator] --> RAW[(MySQL Raw Tables)]
        RAW --> IP[Ingestion Pipeline]
    end

    subgraph "ML Pipeline (Offline)"
        FE[Feature Engineering] --> TRAIN[Model Training]
        TRAIN --> REG[MLflow Model Registry]
    end

    subgraph "Service Layer (Online)"
        API[FastAPI Backend] --> AGENT[LangChain Agent]
        AGENT --> TOOLS[Analysis Tools]
        TOOLS --> REG
        TOOLS --> SQL[(Feature Store)]
    end

    subgraph "Presentation"
        UI[Streamlit Dashboard] --> API
    end
```

---

## 🛠️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Frameworks** | FastAPI, Streamlit, LangChain |
| **Machine Learning** | Scikit-learn, Causal-learn, Lifetimes, Lifelines |
| **Data Engineering** | Pandas, SQLAlchemy, MySQL |
| **MLOps** | MLflow, Docker, GitHub Actions |
| **Cloud** | AWS (RDS, ECS, S3, ECR) |

---

## ⚙️ Quick Start

### 1. Environment Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/chikien07012006/FinChat-Analytics.git
cd FinChat-Analytics
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root directory:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=finchat
DB_USER=root
DB_PASSWORD=your_password
OPENAI_API_KEY=your_key
```

### 3. Data Initialization
Initialize the database and generate synthetic banking data:
```bash
# Create tables
# Run SQL script: data/table_design.sql

# Generate & Ingest data
python data/generate_bank_data.py
python data/ingestion_pipeline.py
```

### 4. Run the Pipeline
Train models and register them with MLflow:
```bash
python pipeline/train_all_models.py
```

---

## 📅 Roadmap

- [x] Phase 1: Synthetic Data Infrastructure
- [x] Phase 2: Core Predictive ML Pipeline
- [/] Phase 3: AI Agent & Integration (In Progress)
- [ ] Phase 4: Streamlit Dashboard Deployment
- [ ] Phase 5: Production Deployment on AWS

