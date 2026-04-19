from ingestion_pipeline import get_mysql_engine
from sqlalchemy import text

engine = get_mysql_engine()

with engine.connect() as conn:
    print("Total customers:", conn.execute(text("SELECT COUNT(*) FROM customer_data")).scalar())
    print("Total transactions:", conn.execute(text("SELECT COUNT(*) FROM raw_transactions")).scalar())
    print("Sample customer:", conn.execute(text("SELECT * FROM customer_data LIMIT 1")).fetchone())