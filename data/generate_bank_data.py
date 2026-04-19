import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)
N_CUSTOMERS = 5000          
N_TRANSACTIONS = 80000     # ~16 giao dịch/khách 

# 1 Customer master data
customers = pd.DataFrame({
    'customer_id': [f'CUST{str(i).zfill(6)}' for i in range(N_CUSTOMERS)],
    'tenant_id': 'BANK001',                                 
    'full_name': np.random.choice(['Nguyễn Văn A', 'Trần Thị B', ...], N_CUSTOMERS), 
    'age': np.random.normal(35, 8, N_CUSTOMERS).astype(int).clip(18, 70),
    'gender': np.random.choice(['Male', 'Female'], N_CUSTOMERS, p=[0.48, 0.52]),
    'city': np.random.choice(['Hà Nội', 'TP.HCM', 'Đà Nẵng', 'Cần Thơ', 'Hải Phòng'], N_CUSTOMERS, p=[0.3,0.35,0.15,0.1,0.1]),
    'signup_date': pd.date_range('2022-01-01', '2025-01-01', N_CUSTOMERS),
    'tenure_months': np.random.randint(1, 48, N_CUSTOMERS),
    'segment_initial': np.random.choice(['Mass', 'Premium', 'VIP'], N_CUSTOMERS, p=[0.7, 0.25, 0.05])
})

# 2 Raw transactions 
start_date = datetime(2023, 1, 1)
dates = start_date + pd.to_timedelta(np.random.randint(0, 1000, N_TRANSACTIONS), unit='D')

transactions = pd.DataFrame({
    'transaction_id': [f'TXN{str(i).zfill(8)}' for i in range(N_TRANSACTIONS)],
    'customer_id': np.random.choice(customers['customer_id'], N_TRANSACTIONS),
    'tenant_id': 'BANK001',
    'transaction_date': dates,
    'amount': np.random.lognormal(7, 1.5, N_TRANSACTIONS).round(2).clip(10_000, 50_000_000),  # VND, skewed
    'transaction_type': np.random.choice(['DEPOSIT', 'WITHDRAW', 'PAYMENT', 'TRANSFER', 'FEE'], N_TRANSACTIONS, p=[0.4,0.25,0.2,0.1,0.05]),
    'channel': np.random.choice(['APP', 'INTERNET_BANKING', 'BRANCH', 'ATM', 'POS'], N_TRANSACTIONS, p=[0.55,0.25,0.1,0.05,0.05]),
    'status': np.random.choice(['SUCCESS', 'FAILED'], N_TRANSACTIONS, p=[0.98, 0.02]),
    'category': np.random.choice(['Shopping', 'Bill', 'Salary', 'Investment', 'Other'], N_TRANSACTIONS)
})

# 3 Thêm treatment (cho Uplift Modeling)
customers['received_promotion'] = np.random.choice([0, 1], N_CUSTOMERS, p=[0.7, 0.3])
customers['promotion_type'] = customers['received_promotion'].apply(lambda x: np.random.choice(['Cashback 10%', 'Fee waiver', 'Voucher']) if x else None)

# 4 Tạo churn label (dùng cho training)
customers['churn'] = 0
# Rule-based + random noise
high_risk = (customers['tenure_months'] < 6) | (customers['age'] < 25)
customers.loc[high_risk, 'churn'] = np.random.choice([0,1], high_risk.sum(), p=[0.3, 0.7])

# Thêm một ít random noise (5-10%) để tránh model học thuộc lòng rule
# noise_idx = customers.sample(frac=0.08, random_state=42).index
# customers.loc[noise_idx, 'churn'] = 1 - customers.loc[noise_idx, 'churn']

# Cải tiến: Rule-based churn definition (càng nhiều rule càng tốt)
# conditions = (
#     (customers['recency_days'] > 90) |                                   # Lâu không giao dịch
#     (customers['freq_90d'] == 0) |                                       # Không có giao dịch trong 90 ngày gần nhất
#     ((customers['frequency'] > 5) & (customers['freq_ratio'] < 0.4)) |   # Tần suất giảm mạnh
#     (customers['monetary_90d'] / (customers['monetary_value'] + 1) < 0.3) |  # Doanh thu gần đây giảm mạnh
#     (customers['tenure_months'] < 3) |                                   # Khách mới rất dễ churn
#     (customers['avg_days_between'] > 60)                                 # Khoảng cách giao dịch ngày càng xa
# )

# # Gán churn = 1 cho những khách thỏa mãn >= 2 conditions
# customers.loc[conditions, 'churn'] = 1

print(f"Generated {len(customers):,} customers and {len(transactions):,} transactions")
customers.to_csv('data/customers.csv', index=False)
transactions.to_csv('data/raw_transactions.csv', index=False)