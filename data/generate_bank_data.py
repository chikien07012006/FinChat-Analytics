from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd


N_CUSTOMERS = 5000
N_TRANSACTIONS = 80000
DEFAULT_TENANT_ID = "BANK001"


def generate_mock_bank_data(
    n_customers: int = N_CUSTOMERS,
    n_transactions: int = N_TRANSACTIONS,
    tenant_id: str = DEFAULT_TENANT_ID,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    customer_ids = [f"CUST{str(i).zfill(6)}" for i in range(n_customers)]
    names = [
        "Nguyen Van A",
        "Tran Thi B",
        "Le Minh C",
        "Pham Anh D",
        "Hoang Thu E",
        "Dang Quang F",
        "Bui Thanh G",
        "Do Mai H",
    ]

    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "tenant_id": tenant_id,
            "full_name": rng.choice(names, n_customers),
            "age": rng.normal(35, 8, n_customers).astype(int).clip(18, 70),
            "gender": rng.choice(["Male", "Female"], n_customers, p=[0.48, 0.52]),
            "city": rng.choice(
                ["Ha Noi", "TP.HCM", "Da Nang", "Can Tho", "Hai Phong"],
                n_customers,
                p=[0.3, 0.35, 0.15, 0.1, 0.1],
            ),
            "signup_date": pd.date_range("2022-01-01", "2025-01-01", n_customers),
            "tenure_months": rng.integers(1, 48, n_customers),
            "segment_initial": rng.choice(["Mass", "Premium", "VIP"], n_customers, p=[0.7, 0.25, 0.05]),
        }
    )

    start_date = datetime(2023, 1, 1)
    dates = start_date + pd.to_timedelta(rng.integers(0, 1000, n_transactions), unit="D")
    transactions = pd.DataFrame(
        {
            "transaction_id": [f"TXN{str(i).zfill(8)}" for i in range(n_transactions)],
            "customer_id": rng.choice(customers["customer_id"], n_transactions),
            "tenant_id": tenant_id,
            "transaction_date": dates,
            "amount": rng.lognormal(7, 1.5, n_transactions).round(2).clip(10_000, 50_000_000),
            "transaction_type": rng.choice(
                ["DEPOSIT", "WITHDRAW", "PAYMENT", "TRANSFER", "FEE"],
                n_transactions,
                p=[0.4, 0.25, 0.2, 0.1, 0.05],
            ),
            "channel": rng.choice(
                ["APP", "INTERNET_BANKING", "BRANCH", "ATM", "POS"],
                n_transactions,
                p=[0.55, 0.25, 0.1, 0.05, 0.05],
            ),
            "status": rng.choice(["SUCCESS", "FAILED"], n_transactions, p=[0.98, 0.02]),
            "category": rng.choice(["Shopping", "Bill", "Salary", "Investment", "Other"], n_transactions),
        }
    )

    customers["received_promotion"] = rng.choice([False, True], n_customers, p=[0.7, 0.3])
    promo_types = rng.choice(["Cashback 10%", "Fee waiver", "Voucher"], n_customers)
    customers["promotion_type"] = np.where(customers["received_promotion"], promo_types, None)

    customers["churn"] = False
    high_risk = (customers["tenure_months"] < 6) | (customers["age"] < 25)
    customers.loc[high_risk, "churn"] = rng.choice([False, True], int(high_risk.sum()), p=[0.3, 0.7])

    return customers, transactions


if __name__ == "__main__":
    customers_df, transactions_df = generate_mock_bank_data()
    print(f"Generated {len(customers_df):,} customers and {len(transactions_df):,} transactions")
    customers_df.to_csv("customers.csv", index=False)
    transactions_df.to_csv("raw_transactions.csv", index=False)
