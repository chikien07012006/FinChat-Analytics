-- Supabase/Postgres schema for FinChat Analytics.
-- Runtime analytics access is through FastAPI + SQLAlchemy, not browser REST.

CREATE TABLE IF NOT EXISTS customer_data (
    customer_id          varchar(20) PRIMARY KEY,
    tenant_id            varchar(20) NOT NULL DEFAULT 'BANK001',
    full_name            varchar(100),
    age                  smallint CHECK (age BETWEEN 0 AND 120),
    gender               text CHECK (gender IN ('Male', 'Female', 'Other')),
    city                 varchar(50),
    signup_date          date NOT NULL,
    tenure_months        smallint CHECK (tenure_months >= 0),
    segment_initial      varchar(20),
    received_promotion   boolean NOT NULL DEFAULT false,
    promotion_type       varchar(50),
    churn                boolean NOT NULL DEFAULT false,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_customer_data_tenant ON customer_data (tenant_id);
CREATE INDEX IF NOT EXISTS idx_customer_data_signup ON customer_data (signup_date);
CREATE INDEX IF NOT EXISTS idx_customer_data_churn ON customer_data (churn);

CREATE TABLE IF NOT EXISTS raw_transactions (
    transaction_id      varchar(30) PRIMARY KEY,
    customer_id         varchar(20) NOT NULL REFERENCES customer_data(customer_id) ON DELETE CASCADE,
    tenant_id           varchar(20) NOT NULL DEFAULT 'BANK001',
    transaction_date    timestamptz NOT NULL,
    amount              numeric(15, 2) NOT NULL CHECK (amount >= 0),
    transaction_type    text CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAW', 'PAYMENT', 'TRANSFER', 'FEE')),
    channel             text CHECK (channel IN ('APP', 'INTERNET_BANKING', 'BRANCH', 'ATM', 'POS')),
    status              text CHECK (status IN ('SUCCESS', 'FAILED')),
    category            varchar(50),
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_transactions_customer_date ON raw_transactions (customer_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_raw_transactions_date ON raw_transactions (transaction_date);
CREATE INDEX IF NOT EXISTS idx_raw_transactions_tenant ON raw_transactions (tenant_id);

CREATE TABLE IF NOT EXISTS customer_features (
    customer_id          varchar(20) PRIMARY KEY REFERENCES customer_data(customer_id) ON DELETE CASCADE,
    tenant_id            varchar(20) NOT NULL,
    rfm_recency          smallint,
    rfm_frequency        integer,
    rfm_monetary         numeric(15, 2),
    rfm_score            varchar(5),
    rfm_segment          varchar(20),
    clv_12m              numeric(15, 2),
    churn_probability    numeric(8, 6),
    time_to_churn_days   integer,
    uplift_score         numeric(8, 6),
    scoring_date         timestamptz,
    model_version        varchar(100),
    last_updated         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_customer_features_tenant ON customer_features (tenant_id);

ALTER TABLE customer_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_features ENABLE ROW LEVEL SECURITY;
