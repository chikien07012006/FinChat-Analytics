import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def get_database_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is required. Use the Supabase Postgres SQLAlchemy URL.")
    
    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=10,           # max connections
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,      # recycle connection sau 1h
    )
    logger.info("Database engine created successfully (pooled)")
    return engine


def get_mysql_engine():
    """Backward-compatible alias while callers migrate to Supabase Postgres."""
    return get_database_engine()


def ingest_dataframe_to_database(df: pd.DataFrame, table_name: str, engine=None, if_exists: str = "append"):
    if engine is None:
        engine = get_database_engine()

    df = df.copy()
    if "created_at" not in df.columns:
        df["created_at"] = pd.Timestamp.now()
    
    try:
        logger.info("Ingesting %s rows into table %s", len(df), table_name)

        df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,
            index=False,
            chunksize=20_000,
            method='multi'
        )
        
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        
        logger.info(f"Ingested {len(df):,} rows into `{table_name}` | Total rows now: {result}")
        return int(len(df))
        
    except Exception as e:
        logger.error(f"Error ingesting table {table_name}: {str(e)}", exc_info=True)
        raise


def ingest_csv_to_database(csv_path: str, table_name: str, engine=None, if_exists: str = "append"):
    df = pd.read_csv(csv_path)
    return ingest_dataframe_to_database(df, table_name, engine=engine, if_exists=if_exists)


def ingest_csv_to_mysql(csv_path: str, table_name: str, engine=None, if_exists: str = "append"):
    """Backward-compatible alias for older scripts."""
    return ingest_csv_to_database(csv_path, table_name, engine=engine, if_exists=if_exists)

if __name__ == "__main__":
    engine = get_database_engine()
    
    ingest_csv_to_database(
        csv_path="customers.csv",
        table_name="customer_data",
        engine=engine,
        if_exists="append"     
    )
    
    ingest_csv_to_database(
        csv_path="raw_transactions.csv",
        table_name="raw_transactions",
        engine=engine,
        if_exists="append"
    )
    # lưu ý chỉ chạy 1 lần, chạy nhiều lần bị duplicate data
    print("\n INGESTION COMPLETED SUCCESSFULLY!")
