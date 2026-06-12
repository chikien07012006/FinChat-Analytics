import argparse

from sqlalchemy import text

from data.generate_bank_data import DEFAULT_TENANT_ID, generate_mock_bank_data
from data.ingestion_pipeline import get_database_engine, ingest_dataframe_to_database


def seed_supabase(
    n_customers: int,
    n_transactions: int,
    tenant_id: str = DEFAULT_TENANT_ID,
    reset: bool = True,
) -> None:
    customers, transactions = generate_mock_bank_data(
        n_customers=n_customers,
        n_transactions=n_transactions,
        tenant_id=tenant_id,
    )
    engine = get_database_engine()

    if reset:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM customer_features WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            conn.execute(text("DELETE FROM raw_transactions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            conn.execute(text("DELETE FROM customer_data WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})

    ingest_dataframe_to_database(customers, "customer_data", engine=engine, if_exists="append")
    ingest_dataframe_to_database(transactions, "raw_transactions", engine=engine, if_exists="append")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Supabase Postgres with FinChat mock data.")
    parser.add_argument("--customers", type=int, default=5000)
    parser.add_argument("--transactions", type=int, default=80000)
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--no-reset", action="store_true", help="Append rows instead of clearing the tenant first.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed_supabase(
        n_customers=args.customers,
        n_transactions=args.transactions,
        tenant_id=args.tenant_id,
        reset=not args.no_reset,
    )
    print("Supabase seed completed.")
