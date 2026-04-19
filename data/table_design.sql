CREATE DATABASE finchat;
Use finchat;

-- 1. customer_data (master table)
CREATE TABLE customer_data (
    customer_id         VARCHAR(20) PRIMARY KEY,
    tenant_id           VARCHAR(20) NOT NULL DEFAULT 'BANK001',
    full_name           VARCHAR(100),
    age                 TINYINT UNSIGNED,
    gender              ENUM('Male', 'Female', 'Other'),
    city                VARCHAR(50),
    signup_date         DATE NOT NULL,
    tenure_months       SMALLINT UNSIGNED,
    segment_initial     VARCHAR(20),
    received_promotion  TINYINT(1) DEFAULT 0,
    promotion_type      VARCHAR(50),
    churn               TINYINT(1) DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id),
    INDEX idx_signup (signup_date),
    INDEX idx_churn (churn)
);

-- 2. raw_transactions (granular, quan trọng nhất)
CREATE TABLE raw_transactions (
    transaction_id     VARCHAR(30) PRIMARY KEY,
    customer_id        VARCHAR(20) NOT NULL,
    tenant_id          VARCHAR(20) NOT NULL DEFAULT 'BANK001',
    transaction_date   DATETIME NOT NULL,
    amount             DECIMAL(15,2) NOT NULL,
    transaction_type   ENUM('DEPOSIT','WITHDRAW','PAYMENT','TRANSFER','FEE'),
    channel            ENUM('APP','INTERNET_BANKING','BRANCH','ATM','POS'),
    status             ENUM('SUCCESS','FAILED'),
    category           VARCHAR(50),
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (customer_id) REFERENCES customer_data(customer_id) ON DELETE CASCADE,
    INDEX idx_customer_date (customer_id, transaction_date),   
    INDEX idx_date (transaction_date),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB;
-- PARTITION BY RANGE (YEAR(transaction_date)) (               -- for scaling 
--     PARTITION p2023 VALUES LESS THAN (2024),
--     PARTITION p2024 VALUES LESS THAN (2025),
--     PARTITION p2025 VALUES LESS THAN (2026),
--     PARTITION p_future VALUES LESS THAN MAXVALUE
-- );

-- 3. customer_features (lưu pre-computed features + model outputs)
CREATE TABLE customer_features (
    customer_id          VARCHAR(20) PRIMARY KEY,
    tenant_id            VARCHAR(20) NOT NULL,
    rfm_recency          SMALLINT,
    rfm_frequency        SMALLINT,
    rfm_monetary         DECIMAL(15,2),
    rfm_score            VARCHAR(5),           -- ví dụ: '555'
    rfm_segment          VARCHAR(20),          -- Champions, At Risk...
    clv_12m              DECIMAL(15,2),
    churn_probability    DECIMAL(5,4),
    time_to_churn_days   INT,                  -- từ Survival Analysis
    uplift_score         DECIMAL(5,4),         -- từ Uplift model
    last_updated         DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer_data(customer_id)
) ENGINE=InnoDB;