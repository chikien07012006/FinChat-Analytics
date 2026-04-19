import pandas as pd
import numpy as np
from datetime import datetime
import logging
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine
from data.ingestion_pipeline import get_mysql_engine

logger = logging.getLogger(__name__)

class CustomerFeatureEngineer:
    def __init__(self, snapshot_date: Optional[datetime] = None):
        self.snapshot_date = pd.Timestamp(snapshot_date or datetime.now())
        self.raw_features = None
        self.scoring_features = None

    def load_transactions(self, table) -> pd.DataFrame:
        """Load raw transaction data"""

        engine = get_mysql_engine()

        df = pd.read_sql_query("""
        SELECT customer_id, tenant_id, transaction_date, amount 
        FROM {table} 
        WHERE amount > 0
        """, engine)
        
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        df = df.sort_values(['customer_id', 'transaction_date'])

        logger.info(f"Loaded {len(df):,} transactions for {df['customer_id'].nunique():,} customers")
    
        return df

    def compute_rfm_and_lifetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """RFM + Tenure (T)"""
        agg = df.groupby('customer_id').agg(
            recency_days=('transaction_date', lambda x: (self.snapshot_date - x.max()).days),
            frequency=('transaction_date', 'nunique'),
            monetary_value=('amount', 'sum'),
            first_tx=('transaction_date', 'min'),
            last_tx=('transaction_date', 'max')
        ).reset_index()
        
        agg['T'] = (self.snapshot_date - agg['first_tx']).dt.days          # Tenure in days
        agg['T_months'] = agg['T'] / 30.44
        agg['recency_months'] = agg['recency_days'] / 30.44
        agg['recency_over_T'] = agg['recency_days'] / (agg['T'] + 1)               # tránh chia 0
        agg['freq_over_T'] = agg['frequency'] / (agg['T_months'] + 1)

        return agg

    def compute_rolling_features(self, df: pd.DataFrame, windows=[30, 90, 180]) -> pd.DataFrame:
        """Rolling frequency & monetary"""
        df = df.copy()
        rolling_list = []

        for window in windows:
            # Tính rolling theo customer
            rolling = (df.set_index('transaction_date')
                       .groupby('customer_id')['amount']
                       .rolling(window, min_periods=1)
                       .agg(['count', 'sum'])
                       .reset_index())

            rolling.rename(columns={
                'count': f'freq_{window}d', # Số lần giao dịch trong vòng window ngày gần nhất
                'sum': f'monetary_{window}d' # Tổng giá trị giao dịch trong vòng window ngày gần nhất
            }, inplace=True)

            # Lấy giá trị mới nhất theo snapshot_date
            latest = rolling.groupby('customer_id').last().reset_index()
            rolling_list.append(latest)

        # Merge tất cả windows
        result = rolling_list[0]
        for r in rolling_list[1:]:
            result = result.merge(r, on=['customer_id'], how='left')

        # Tính thêm ratio
        result['freq_ratio'] = result['freq_90d'] / (result['freq_180d'] + 1)
        result['monetary_ratio'] = result['monetary_90d'] / (result['monetary_180d'] + 1)

        return result

    def compute_behavioral_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Additional behavioral features"""
        df_sorted = df.sort_values(['customer_id', 'transaction_date'])
        df_sorted['prev_date'] = df_sorted.groupby('customer_id')['transaction_date'].shift(1)
        df_sorted['days_between'] = (df_sorted['transaction_date'] - df_sorted['prev_date']).dt.days

        behavioral = df_sorted.groupby('customer_id').agg(
            avg_days_between=('days_between', 'mean'), # Số ngày trung bình giữa 2 lần giao dịch của khách hàng
            std_days_between=('days_between', 'std'), # Độ lệch chuẩn số ngày giữa 2 lần giao dịch của khách hàng
            avg_tx_value=('amount', 'mean'), # Giá trị trung bình của giao dịch
            max_tx_value=('amount', 'max'), # Giá trị lớn nhất của giao dịch
            min_tx_value=('amount', 'min'), # Giá trị nhỏ nhất của giao dịch
            transaction_count_total=('amount', 'count') # Tổng số giao dịch
        ).reset_index()

        # Active days ratio
        active_days = df.groupby('customer_id')['transaction_date'].nunique().reset_index(name='active_days') # Số ngày có giao dịch của khách hàng
        behavioral = behavioral.merge(active_days, on='customer_id')
        
        behavioral['active_days_ratio'] = behavioral['active_days'] / (behavioral['transaction_count_total'] + 1) # Tỷ lệ số ngày có giao dịch so với tổng số giao dịch

        return behavioral

    def compute_promotion_features(self, df: pd.DataFrame) -> pd.DataFrame: # Uplift modeling
        """Xử lý promotion data cho uplift modeling"""
        promo_agg = df.groupby('customer_id').agg(
            received_promotion=('received_promotion', 'max'),           # 1 nếu từng nhận ít nhất 1 lần
            num_promotions=('received_promotion', 'sum'),               # số lần nhận promotion
            promotion_types=('promotion_type', lambda x: list(x.unique()) if len(x.unique()) > 0 else None),
            last_promotion_date=('transaction_date', lambda x: x[df.loc[x.index, 'received_promotion'] == 1].max() if any(df.loc[x.index, 'received_promotion'] == 1) else pd.NaT)
        ).reset_index()
        
        # Tính recency của promotion
        promo_agg['days_since_last_promotion'] = (self.snapshot_date - promo_agg['last_promotion_date'].dt.date).dt.days
        promo_agg['days_since_last_promotion'] = promo_agg['days_since_last_promotion'].fillna(999)  # hoặc giá trị lớn nếu chưa từng nhận
        
        # One-hot hoặc frequency encoding cho promotion_type (nếu nhiều loại) | làm sau ... 
        # Hoặc giữ nguyên categorical để sau encode trong training pipeline
    
    return promo_agg

    def run_feature_engineering(self) -> pd.DataFrame:
        """Main pipeline - trả về full intermediate features"""
        df = self.load_transactions(table='raw_transactions')
        promo_df = self.load_transactions(table='customer_data') #Uplift modeling

        rfm_df = self.compute_rfm_and_lifetime(df)
        rolling_df = self.compute_rolling_features(df)
        behavioral_df = self.compute_behavioral_features(df)
        promo_df = self.compute_promotion_features(promo_df)

        # Merge tất cả
        features = rfm_df.merge(rolling_df, on='customer_id', how='left')
        features = features.merge(behavioral_df, on='customer_id', how='left')
        features = features.merge(promo_df, on='customer_id', how='left')

        # Xử lý Nan value
        for col in ['freq_30d', 'freq_90d', 'freq_180d', 'monetary_30d', 'monetary_90d', 'monetary_180d']:
            features[col] = features[col].fillna(0)
        
        features['avg_days_between'] = features['avg_days_between'].fillna(features['avg_days_between'].median())
        features['std_days_between'] = features['std_days_between'].fillna(0)

        # Thêm metadata
        features['snapshot_date'] = self.snapshot_date
        features['feature_version'] = datetime.now().strftime('%Y%m%d_%H%M')

        self.raw_features = features
        logger.info(f"Feature engineering completed. Shape: {features.shape}")
        
        return features

    def create_scoring_features(self, raw_features: pd.DataFrame, predictions: dict = None) -> pd.DataFrame: # lưu vào bảng customer_features khi đã train và predict xong
        """
        Tạo bảng customer_features cuối cùng từ raw_features + predictions
        predictions là dict chứa output từ các model (churn_probability, clv_12m, ...)
        """
        scoring = raw_features[['customer_id']].copy()
        
        # RFM cơ bản
        #scoring['rfm_recency'] = raw_features['recency_days']
        scoring['rfm_frequency'] = raw_features['frequency']
        scoring['rfm_monetary'] = raw_features['monetary_value']
        
        # RFM Score & Segment (sẽ implement chi tiết ở bước sau)
        scoring['rfm_score'] = None      # Tính sau
        scoring['rfm_segment'] = None    # Champions, At Risk, etc.
        
        # Các prediction từ model
        if predictions:
            for key, value in predictions.items():
                if key in ['clv_12m', 'churn_probability', 'time_to_churn_days', 'uplift_score']:
                    scoring[key] = value
        
        scoring['tenant_id'] = raw_features.get('tenant_id', None)  # nếu có
        scoring['last_updated'] = datetime.now()
        scoring['scoring_date'] = self.snapshot_date
        scoring['model_version'] = 'pending'   # sẽ update sau khi train

        self.scoring_features = scoring
        return scoring

    def save_raw_features(self, path: str = "data/features/raw_features_{date}.parquet"):
        date_str = self.snapshot_date.strftime('%Y%m%d')
        full_path = path.format(date=date_str)
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        self.raw_features.to_parquet(full_path, index=False)
        logger.info(f"Saved raw features to {full_path}")