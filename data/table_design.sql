-- FinChat Analytics Supabase/PostgreSQL schema.
-- Run this in the Supabase SQL editor or through the Supabase MCP migration tool.

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

ALTER TABLE customer_data ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_customer_data_tenant
    ON customer_data (tenant_id);

CREATE INDEX IF NOT EXISTS idx_customer_data_signup
    ON customer_data (signup_date);

CREATE INDEX IF NOT EXISTS idx_customer_data_churn
    ON customer_data (churn);

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

ALTER TABLE raw_transactions ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_raw_transactions_customer_date
    ON raw_transactions (customer_id, transaction_date);

CREATE INDEX IF NOT EXISTS idx_raw_transactions_date
    ON raw_transactions (transaction_date);

CREATE INDEX IF NOT EXISTS idx_raw_transactions_tenant
    ON raw_transactions (tenant_id);

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

ALTER TABLE customer_features ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION set_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

DROP TRIGGER IF EXISTS trg_customer_features_last_updated ON customer_features;

CREATE TRIGGER trg_customer_features_last_updated
BEFORE UPDATE ON customer_features
FOR EACH ROW
EXECUTE FUNCTION set_last_updated();
