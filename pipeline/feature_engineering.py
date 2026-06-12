import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, text
from data.ingestion_pipeline import get_database_engine

class CustomerFeatureEngineer:
    def __init__(self, snapshot_date: Optional[datetime] = None):
        self.snapshot_date = pd.Timestamp(snapshot_date or datetime.now())
        self.raw_features = None
        self.scoring_features = None

    def load_transactions(self, table) -> pd.DataFrame:
        """Load raw transaction data"""
        engine = get_database_engine()
        with engine.connect() as conn:
            df = pd.read_sql_query(text(f"""
            SELECT customer_id, tenant_id, transaction_date, amount 
            FROM {table} 
            WHERE amount > 0
            """), conn)
        
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        df = df.sort_values(['customer_id', 'transaction_date'])

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
        
        agg['T'] = (self.snapshot_date - agg['first_tx']).dt.days
        agg['T_months'] = agg['T'] / 30.44
        agg['recency_months'] = agg['recency_days'] / 30.44
        agg['recency_over_T'] = agg['recency_days'] / (agg['T'] + 1)
        agg['freq_over_T'] = agg['frequency'] / (agg['T_months'] + 1)

        return agg

    def compute_rolling_features(self, df: pd.DataFrame, windows=[30, 90, 180]) -> pd.DataFrame:
        """Rolling frequency & monetary"""
        df = df.copy()
        rolling_list = []

        for window in windows:
            rolling = (df.set_index('transaction_date')
                       .groupby('customer_id')['amount']
                       .rolling(window, min_periods=1)
                       .agg(['count', 'sum'])
                       .reset_index())

            rolling.rename(columns={
                'count': f'freq_{window}d',
                'sum': f'monetary_{window}d'
            }, inplace=True)

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
            avg_days_between=('days_between', 'mean'),
            std_days_between=('days_between', 'std'),
            avg_tx_value=('amount', 'mean'),
            max_tx_value=('amount', 'max'),
            min_tx_value=('amount', 'min'),
            transaction_count_total=('amount', 'count')
        ).reset_index()

        active_days = df.groupby('customer_id')['transaction_date'].nunique().reset_index(name='active_days')
        behavioral = behavioral.merge(active_days, on='customer_id')
        
        behavioral['active_days_ratio'] = behavioral['active_days'] / (behavioral['transaction_count_total'] + 1)

        return behavioral

    def compute_promotion_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process promotion data for uplift modeling"""
        promo_agg = df.groupby('customer_id').agg(
            received_promotion=('received_promotion', 'max'),
            num_promotions=('received_promotion', 'sum'),
            churn=('churn', 'max'),
            promotion_types=('promotion_type', lambda x: list(x.unique()) if len(x.unique()) > 0 else None),
            last_promotion_date=('transaction_date', lambda x: x[df.loc[x.index, 'received_promotion'] == 1].max() if any(df.loc[x.index, 'received_promotion'] == 1) else pd.NaT),
            age=('age', 'first'),
            gender=('gender', 'first'),
            city=('city', 'first'),
            segment_initial=('segment_initial', 'first')
        ).reset_index()
        
        # Tính recency của promotion
        promo_agg['days_since_last_promotion'] = (self.snapshot_date - promo_agg['last_promotion_date']).dt.days
        promo_agg['days_since_last_promotion'] = promo_agg['days_since_last_promotion'].fillna(999)

        return promo_agg

    def compute_conversion_label(self, transactions_df: pd.DataFrame, promo_df: pd.DataFrame) -> pd.DataFrame:
        """Define conversion as activity within 30 days post-promotion"""
        merged = transactions_df.merge(promo_df[['customer_id', 'transaction_date']], on='customer_id', how='inner')
        merged.rename(columns={'transaction_date_y': 'promo_date', 'transaction_date_x': 'tx_date'}, inplace=True)
        
        merged['days_after_promo'] = (merged['tx_date'] - merged['promo_date']).dt.days
        
        # Consider strictly post-signup activity
        merged['is_conversion'] = (merged['days_after_promo'] > 0) & (merged['days_after_promo'] <= 30)
        
        conversion_agg = merged.groupby('customer_id')['is_conversion'].max().astype(int).reset_index(name='conversion')
        
        return conversion_agg

    def run_feature_engineering(self) -> pd.DataFrame:
        """Main feature engineering pipeline"""
        df = self.load_transactions(table='raw_transactions')
        engine = get_database_engine()
        with engine.connect() as conn:
            promo_df = pd.read_sql_query(text("""
                SELECT customer_id, received_promotion, promotion_type, signup_date as transaction_date, churn,
                       age, gender, city, segment_initial
                FROM customer_data
            """), conn)
        promo_df['transaction_date'] = pd.to_datetime(promo_df['transaction_date'])

        rfm_df = self.compute_rfm_and_lifetime(df)
        rolling_df = self.compute_rolling_features(df)
        behavioral_df = self.compute_behavioral_features(df)
        
        # Determine conversion based on post-treatment activity
        conversion_df = self.compute_conversion_label(df, promo_df)
        
        promo_df = self.compute_promotion_features(promo_df)

        # Merge all components
        features = rfm_df.merge(rolling_df, on='customer_id', how='left')
        features = features.merge(behavioral_df, on='customer_id', how='left')
        features = features.merge(promo_df, on='customer_id', how='left')
        features = features.merge(conversion_df, on='customer_id', how='left')

        # Handle missing values
        for col in ['freq_30d', 'freq_90d', 'freq_180d', 'monetary_30d', 'monetary_90d', 'monetary_180d', 'conversion']:
            features[col] = features[col].fillna(0).astype(int) if col == 'conversion' else features[col].fillna(0)
        
        features['avg_days_between'] = features['avg_days_between'].fillna(features['avg_days_between'].median())
        features['std_days_between'] = features['std_days_between'].fillna(0)

        # Churn/Duration for Survival Analysis
        features['churned'] = features['churn'].fillna(0).astype(int)
        features['duration'] = np.where(
            features['churned'] == 1,
            (features['last_tx'] - features['first_tx']).dt.days,
            (self.snapshot_date - features['first_tx']).dt.days
        )
        features['duration'] = features['duration'].clip(lower=1)

        features['snapshot_date'] = self.snapshot_date
        features['feature_version'] = datetime.now().strftime('%Y%m%d_%H%M')

        self.raw_features = features
        
        return features

    def create_scoring_features(self, raw_features: pd.DataFrame, predictions: dict = None) -> pd.DataFrame:
        """Create final customer scoring table from raw features and predictions"""
        scoring = raw_features[['customer_id']].copy()
        
        scoring['rfm_frequency'] = raw_features['frequency']
        scoring['rfm_monetary'] = raw_features['monetary_value']
        
        scoring['rfm_score'] = None
        scoring['rfm_segment'] = None
        
        if predictions:
            for key, value in predictions.items():
                if key in ['clv_12m', 'churn_probability', 'time_to_churn_days', 'uplift_score']:
                    scoring[key] = value
        
        scoring['tenant_id'] = raw_features.get('tenant_id', None)
        scoring['last_updated'] = datetime.now()
        scoring['scoring_date'] = self.snapshot_date
        scoring['model_version'] = 'pending'

        self.scoring_features = scoring
        return scoring

    def save_raw_features(self, path: str = "data/features/raw_features_{date}.parquet"):
        date_str = self.snapshot_date.strftime('%Y%m%d')
        full_path = path.format(date=date_str)
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        self.raw_features.to_parquet(full_path, index=False)
        

def run_feature_engineering() -> pd.DataFrame:
    """Standalone wrapper for CustomerFeatureEngineer.run_feature_engineering"""
    engineer = CustomerFeatureEngineer()
    return engineer.run_feature_engineering()
