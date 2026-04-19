import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def get_mysql_engine():
    db_url = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    
    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=10,           # max connections
        max_overflow=20,
        pool_pre_ping=True,     # fix "MySQL server has gone away"
        pool_recycle=3600,      # recycle connection sau 1h
    )
    logger.info("MySQL engine created successfully (pooled)")
    return engine

def ingest_csv_to_mysql(csv_path: str, table_name: str, engine=None, if_exists: str = "append"):
    if engine is None:
        engine = get_mysql_engine()
    
    try:
        logger.info(f"Ingesting {csv_path} → table {table_name}")
        
        df = pd.read_csv(csv_path)
        
        if 'created_at' not in df.columns:
            df['created_at'] = pd.Timestamp.now()
        
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
        
    except Exception as e:
        logger.error(f"Error ingesting {csv_path}: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    engine = get_mysql_engine()
    
    ingest_csv_to_mysql(
        csv_path="data/customers.csv",
        table_name="customer_data",
        engine=engine,
        if_exists="append"     
    )
    
    ingest_csv_to_mysql(
        csv_path="data/raw_transactions.csv",
        table_name="raw_transactions",
        engine=engine,
        if_exists="append"
    )
    # lưu ý chỉ chạy 1 lần, chạy nhiều lần bị duplicate data
    print("\n INGESTION COMPLETED SUCCESSFULLY!")