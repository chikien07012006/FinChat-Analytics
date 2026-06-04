# Supabase Implementation Summary

This document explains what was changed to make Supabase Postgres store the FinChat mock data persistently, instead of regenerating CSVs and ingesting into MySQL for every run.

## What Changed

The project now uses the Supabase `FinChat` database as the durable mock-data store.

Live Supabase project:

- Project name: `FinChat`
- Project ID: `klvsuurcyhhtfhsfjvcs`
- Database host: `db.klvsuurcyhhtfhsfjvcs.supabase.co`

Seeded live data:

- `customer_data`: 5,000 rows
- `raw_transactions`: 80,000 rows
- `customer_features`: 5,000 rows
- orphan transactions: 0
- orphan feature rows: 0

The normal workflow is now:

```bash
# Only needed when resetting/regenerating mock data
python data/generate_bank_data.py
python data/seed_supabase.py

# Normal analytics/model workflow reads from Supabase
python pipeline/train_all_models.py
```

## Database Schema

The old MySQL schema in `data/table_design.sql` was replaced with Supabase/Postgres DDL.

Key tables:

```sql
CREATE TABLE IF NOT EXISTS customer_data (
    customer_id         VARCHAR(20) PRIMARY KEY,
    tenant_id           VARCHAR(20) NOT NULL DEFAULT 'BANK001',
    full_name           VARCHAR(100),
    age                 SMALLINT CHECK (age BETWEEN 0 AND 120),
    gender              TEXT CHECK (gender IN ('Male', 'Female', 'Other')),
    city                VARCHAR(50),
    signup_date         DATE NOT NULL,
    tenure_months       SMALLINT CHECK (tenure_months >= 0),
    segment_initial     VARCHAR(20),
    received_promotion  BOOLEAN DEFAULT FALSE,
    promotion_type      VARCHAR(50),
    churn               BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```sql
CREATE TABLE IF NOT EXISTS raw_transactions (
    transaction_id     VARCHAR(30) PRIMARY KEY,
    customer_id        VARCHAR(20) NOT NULL,
    tenant_id          VARCHAR(20) NOT NULL DEFAULT 'BANK001',
    transaction_date   TIMESTAMP NOT NULL,
    amount             NUMERIC(15,2) NOT NULL CHECK (amount >= 0),
    transaction_type   TEXT CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAW', 'PAYMENT', 'TRANSFER', 'FEE')),
    channel            TEXT CHECK (channel IN ('APP', 'INTERNET_BANKING', 'BRANCH', 'ATM', 'POS')),
    status             TEXT CHECK (status IN ('SUCCESS', 'FAILED')),
    category           VARCHAR(50),
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_raw_transactions_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer_data(customer_id)
        ON DELETE CASCADE
);
```

```sql
CREATE TABLE IF NOT EXISTS customer_features (
    customer_id          VARCHAR(20) PRIMARY KEY,
    tenant_id            VARCHAR(20) NOT NULL,
    rfm_recency          SMALLINT,
    rfm_frequency        SMALLINT,
    rfm_monetary         NUMERIC(15,2),
    rfm_score            VARCHAR(5),
    rfm_segment          VARCHAR(20),
    clv_12m              NUMERIC(15,2),
    churn_probability    NUMERIC(5,4),
    time_to_churn_days   INTEGER,
    uplift_score         NUMERIC(5,4),
    scoring_date         TIMESTAMP,
    model_version        VARCHAR(50),
    last_updated         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_features_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer_data(customer_id)
        ON DELETE CASCADE
);
```

Row Level Security was enabled on all three public tables:

```sql
ALTER TABLE customer_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_features ENABLE ROW LEVEL SECURITY;
```

No public RLS policies were added yet. That means browser/client access is blocked by default, while backend code using the database connection can still operate.

## Python Database Connection

The MySQL-specific connection was replaced with a neutral SQLAlchemy connection that reads `DATABASE_URL`.

Relevant snippet from `data/ingestion_pipeline.py`:

```python
def get_db_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required for Supabase/PostgreSQL access.")

    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    logger.info("Database engine created successfully")
    return engine
```

A temporary compatibility alias remains:

```python
def get_mysql_engine() -> Engine:
    """Compatibility alias during the MySQL-to-Supabase transition."""
    return get_db_engine()
```

`config.py` now exposes `DATABASE_URL`:

```python
class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
```

`.env.example` now points to Supabase:

```env
DATABASE_URL=postgresql://postgres:<password>@db.klvsuurcyhhtfhsfjvcs.supabase.co:5432/postgres?sslmode=require
SUPABASE_URL=https://klvsuurcyhhtfhsfjvcs.supabase.co
TENANT_ID=BANK001
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Seeding Flow

`data/seed_supabase.py` is the new command entrypoint:

```python
from ingestion_pipeline import main


if __name__ == "__main__":
    main()
```

The actual seeding logic lives in `data/ingestion_pipeline.py`.

It resets tables by default:

```python
def reset_mock_tables(engine: Engine | None = None) -> None:
    if engine is None:
        engine = get_db_engine()

    with engine.begin() as conn:
        conn.execute(text("""
            TRUNCATE TABLE
                customer_features,
                raw_transactions,
                customer_data
            RESTART IDENTITY CASCADE
        """))
```

Then it upserts the CSV rows:

```python
def seed_mock_data(
    customers_csv: str | Path = DEFAULT_CUSTOMERS_CSV,
    transactions_csv: str | Path = DEFAULT_TRANSACTIONS_CSV,
    reset: bool = True,
) -> None:
    engine = get_db_engine()

    if reset:
        reset_mock_tables(engine)

    seed_csv_to_supabase(customers_csv, "customer_data", engine=engine, mode="upsert")
    seed_csv_to_supabase(transactions_csv, "raw_transactions", engine=engine, mode="upsert")
    refresh_mock_customer_features(engine)
```

The CSV normalization handles Postgres-friendly types:

```python
if table_name == "customer_data":
    if "signup_date" in df.columns:
        df["signup_date"] = pd.to_datetime(df["signup_date"]).dt.date

    for column in ["received_promotion", "churn"]:
        if column in df.columns:
            df[column] = df[column].fillna(0).astype(bool)

if table_name == "raw_transactions" and "transaction_date" in df.columns:
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
```

## Feature Engineering Reads From Supabase

`pipeline/feature_engineering.py` now imports the Supabase/Postgres engine:

```python
from data.ingestion_pipeline import get_db_engine
```

The existing analytics queries still read the same logical tables:

```python
engine = get_db_engine()
with engine.connect() as conn:
    df = pd.read_sql_query(text("""
    SELECT customer_id, tenant_id, transaction_date, amount
    FROM raw_transactions
    WHERE amount > 0
    """), conn)
```

This means the pipeline code does not need to regenerate or ingest mock data during normal runs.

## Validation

`data/test_db_connection.py` now verifies Supabase row counts and referential integrity:

```python
total_customers = conn.execute(text("SELECT COUNT(*) FROM customer_data")).scalar()
total_transactions = conn.execute(text("SELECT COUNT(*) FROM raw_transactions")).scalar()
total_features = conn.execute(text("SELECT COUNT(*) FROM customer_features")).scalar()
orphan_transactions = conn.execute(text("""
    SELECT COUNT(*)
    FROM raw_transactions rt
    LEFT JOIN customer_data cd ON cd.customer_id = rt.customer_id
    WHERE cd.customer_id IS NULL
""")).scalar()
```

Run it with a valid local `.env`:

```bash
python data/test_db_connection.py
```

## Verification Completed

Completed checks:

- Supabase schema created successfully.
- Live mock data seeded successfully.
- Live row counts verified.
- Live orphan checks returned `0`.
- Python syntax checks passed for changed Python files.
- Supabase advisors were checked.

Current Supabase advisor note:

- RLS is enabled with no policies on public tables.
- This is acceptable for backend-only database access.
- Add RLS policies later if a frontend uses Supabase anon/client access directly.

