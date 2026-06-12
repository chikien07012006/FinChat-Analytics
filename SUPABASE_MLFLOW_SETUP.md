# Supabase Auth, Database, and MLflow Setup

## Supabase Project

Project: `FinChat-Analytics`

- Project ref: `mwtfqvjglddmllddmuim`
- API URL: `https://mwtfqvjglddmllddmuim.supabase.co`
- Database host: `db.mwtfqvjglddmllddmuim.supabase.co`

The schema migration has been applied through the Supabase MCP and is also stored locally in `supabase/migrations/202606130001_create_finchat_schema.sql`.

## Local `.env`

Create `.env` from `.env.example` and fill in:

```env
DATABASE_URL=postgresql+psycopg://postgres:<db-password>@db.mwtfqvjglddmllddmuim.supabase.co:5432/postgres?sslmode=require
SUPABASE_URL=https://mwtfqvjglddmllddmuim.supabase.co
SUPABASE_ANON_KEY=<project-anon-or-publishable-key>
STREAMLIT_BASE_URL=http://localhost:8501
MLFLOW_TRACKING_URI=mlruns
```

## Google OAuth

In Supabase Dashboard:

1. Open Authentication > Providers > Google.
2. Enable Google.
3. Add the Google OAuth client ID and client secret.
4. Add `http://localhost:8501` to the allowed redirect URLs.

In Google Cloud Console:

1. Create a Web OAuth client.
2. Add `http://localhost:8501` as an authorized JavaScript origin.
3. Add the Supabase callback URL shown in the Supabase Google provider page as an authorized redirect URI.

## Seed Mock Data

After `.env` is configured:

```bash
python -m data.seed_supabase
```

Use smaller data for a quick smoke test:

```bash
python -m data.seed_supabase --customers 100 --transactions 1000
```

## Run Locally

```bash
python -m uvicorn backend.main:app --reload
streamlit run frontend/app.py
```

## Train and Log to MLflow

```bash
python -m pipeline.train_all_models
```

Local MLflow artifacts are written to `mlruns/`, which is gitignored.
