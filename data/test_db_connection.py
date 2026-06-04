from sqlalchemy import text

from ingestion_pipeline import get_db_engine


engine = get_db_engine()

with engine.connect() as conn:
    total_customers = conn.execute(text("SELECT COUNT(*) FROM customer_data")).scalar()
    total_transactions = conn.execute(text("SELECT COUNT(*) FROM raw_transactions")).scalar()
    total_features = conn.execute(text("SELECT COUNT(*) FROM customer_features")).scalar()
    orphan_transactions = conn.execute(text("""
        SELECT COUNT(*)
        FROM raw_transactions rt
        LEFT JOIN customer_data cd ON cd.customer_id = rt.customer_id
        WHERE cd.customer_id IS NULL
    """)).scalar()
    sample_customer = conn.execute(text("SELECT * FROM customer_data LIMIT 1")).fetchone()

print("Total customers:", total_customers)
print("Total transactions:", total_transactions)
print("Total features:", total_features)
print("Orphan transactions:", orphan_transactions)
print("Sample customer:", sample_customer)

if orphan_transactions:
    raise SystemExit("Database integrity check failed: orphan transactions found")
