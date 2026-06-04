import argparse
import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CUSTOMERS_CSV = PROJECT_ROOT / "customers.csv"
DEFAULT_TRANSACTIONS_CSV = PROJECT_ROOT / "raw_transactions.csv"

TABLE_PRIMARY_KEYS = {
    "customer_data": "customer_id",
    "raw_transactions": "transaction_id",
}


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


def get_mysql_engine() -> Engine:
    """Compatibility alias during the MySQL-to-Supabase transition."""
    return get_db_engine()


def _normalize_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    df = df.copy()

    if "created_at" not in df.columns:
        df["created_at"] = pd.Timestamp.now()

    if table_name == "customer_data":
        if "signup_date" in df.columns:
            df["signup_date"] = pd.to_datetime(df["signup_date"]).dt.date

        for column in ["received_promotion", "churn"]:
            if column in df.columns:
                df[column] = df[column].fillna(0).astype(bool)

        if "promotion_type" in df.columns:
            df["promotion_type"] = df["promotion_type"].where(pd.notna(df["promotion_type"]), None)

    if table_name == "raw_transactions" and "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    return df


def _upsert_dataframe(df: pd.DataFrame, table_name: str, engine: Engine) -> None:
    primary_key = TABLE_PRIMARY_KEYS[table_name]
    temp_table = f"tmp_{table_name}_seed"

    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))

    df.to_sql(
        name=temp_table,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=20_000,
        method="multi",
    )

    columns = list(df.columns)
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    update_columns = [column for column in columns if column != primary_key]
    update_clause = ", ".join(
        f'"{column}" = EXCLUDED."{column}"' for column in update_columns
    )

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO "{table_name}" ({quoted_columns})
            SELECT {quoted_columns}
            FROM "{temp_table}"
            ON CONFLICT ("{primary_key}") DO UPDATE SET
                {update_clause}
        """))
        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))


def seed_csv_to_supabase(
    csv_path: str | Path,
    table_name: str,
    engine: Engine | None = None,
    mode: str = "upsert",
) -> None:
    if table_name not in TABLE_PRIMARY_KEYS:
        raise ValueError(f"Unsupported seed table: {table_name}")

    if mode not in {"append", "upsert"}:
        raise ValueError("mode must be either 'append' or 'upsert'")

    if engine is None:
        engine = get_db_engine()

    csv_path = Path(csv_path)
    logger.info("Seeding %s into %s with mode=%s", csv_path, table_name, mode)

    df = pd.read_csv(csv_path)
    df = _normalize_dataframe(df, table_name)

    if mode == "append":
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            chunksize=20_000,
            method="multi",
        )
    else:
        _upsert_dataframe(df, table_name, engine)

    with engine.connect() as conn:
        total_rows = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()

    logger.info("Seeded %s rows into %s | total rows: %s", len(df), table_name, total_rows)


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

    logger.info("Reset mock data tables")


def refresh_mock_customer_features(engine: Engine | None = None) -> None:
    if engine is None:
        engine = get_db_engine()

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO customer_features (
                customer_id,
                tenant_id,
                rfm_recency,
                rfm_frequency,
                rfm_monetary,
                rfm_score,
                rfm_segment,
                clv_12m,
                churn_probability,
                time_to_churn_days,
                uplift_score,
                scoring_date,
                model_version
            )
            WITH rfm AS (
                SELECT
                    cd.customer_id,
                    cd.tenant_id,
                    cd.churn,
                    greatest(0, (CURRENT_DATE - max(rt.transaction_date)::date))::int AS recency_days,
                    count(rt.transaction_id)::int AS frequency,
                    coalesce(sum(rt.amount), 0)::numeric(15,2) AS monetary
                FROM customer_data cd
                LEFT JOIN raw_transactions rt ON rt.customer_id = cd.customer_id
                GROUP BY cd.customer_id, cd.tenant_id, cd.churn
            ), scored AS (
                SELECT
                    *,
                    ntile(5) OVER (ORDER BY recency_days DESC) AS recency_score,
                    ntile(5) OVER (ORDER BY frequency ASC) AS frequency_score,
                    ntile(5) OVER (ORDER BY monetary ASC) AS monetary_score
                FROM rfm
            )
            SELECT
                customer_id,
                tenant_id,
                recency_days::smallint,
                frequency::smallint,
                monetary,
                recency_score::text || frequency_score::text || monetary_score::text AS rfm_score,
                CASE
                    WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'Champions'
                    WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At Risk'
                    WHEN recency_score <= 2 AND frequency_score <= 2 THEN 'Lost'
                    WHEN frequency_score >= 4 THEN 'Loyal'
                    ELSE 'Potential'
                END AS rfm_segment,
                round((monetary * (0.08 + random() * 0.18))::numeric, 2) AS clv_12m,
                CASE
                    WHEN churn THEN round((0.65 + random() * 0.30)::numeric, 4)
                    ELSE round((0.02 + random() * 0.35)::numeric, 4)
                END AS churn_probability,
                CASE
                    WHEN churn THEN 0
                    ELSE (30 + floor(random() * 365)::int)
                END AS time_to_churn_days,
                round((-0.05 + random() * 0.30)::numeric, 4) AS uplift_score,
                CURRENT_TIMESTAMP AS scoring_date,
                'mock_seed_v1' AS model_version
            FROM scored
            ON CONFLICT (customer_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                rfm_recency = EXCLUDED.rfm_recency,
                rfm_frequency = EXCLUDED.rfm_frequency,
                rfm_monetary = EXCLUDED.rfm_monetary,
                rfm_score = EXCLUDED.rfm_score,
                rfm_segment = EXCLUDED.rfm_segment,
                clv_12m = EXCLUDED.clv_12m,
                churn_probability = EXCLUDED.churn_probability,
                time_to_churn_days = EXCLUDED.time_to_churn_days,
                uplift_score = EXCLUDED.uplift_score,
                scoring_date = EXCLUDED.scoring_date,
                model_version = EXCLUDED.model_version
        """))

    logger.info("Refreshed mock customer feature rows")


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

    with engine.connect() as conn:
        orphan_count = conn.execute(text("""
            SELECT COUNT(*)
            FROM raw_transactions rt
            LEFT JOIN customer_data cd ON cd.customer_id = rt.customer_id
            WHERE cd.customer_id IS NULL
        """)).scalar()

    if orphan_count:
        raise RuntimeError(f"Found {orphan_count} transactions without customer rows")

    logger.info("Supabase mock data seed completed successfully")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FinChat mock data into Supabase/PostgreSQL.")
    parser.add_argument("--customers-csv", default=str(DEFAULT_CUSTOMERS_CSV))
    parser.add_argument("--transactions-csv", default=str(DEFAULT_TRANSACTIONS_CSV))
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not truncate existing mock tables before upserting CSV rows.",
    )
    args = parser.parse_args()

    seed_mock_data(
        customers_csv=args.customers_csv,
        transactions_csv=args.transactions_csv,
        reset=not args.no_reset,
    )


if __name__ == "__main__":
    main()
