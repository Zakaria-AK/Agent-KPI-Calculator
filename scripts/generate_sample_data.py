"""Generates a small synthetic churn CSV to smoke-test the agent against."""

import random
from datetime import date, timedelta
from pathlib import Path

random.seed(0)

REGIONS = ["North", "South", "East", "West"]
PLANS = ["Basic", "Pro", "Enterprise"]
START = date(2024, 1, 1)
MONTHS = 24

rows = ["customer_id,region,plan,monthly_fee,signup_date,churn_date"]
for customer_id in range(1, 201):
    region = random.choice(REGIONS)
    plan = random.choice(PLANS)
    fee = {"Basic": 9.99, "Pro": 29.99, "Enterprise": 99.99}[plan]
    signup_offset = random.randint(0, MONTHS * 30 - 30)
    signup = START + timedelta(days=signup_offset)

    churns = random.random() < 0.35
    churn_date = ""
    if churns:
        churn_offset = random.randint(30, MONTHS * 30 - signup_offset)
        churn_date = (signup + timedelta(days=churn_offset)).isoformat()

    rows.append(f"{customer_id},{region},{plan},{fee},{signup.isoformat()},{churn_date}")

out_path = Path(__file__).resolve().parent.parent / "data" / "sample_churn.csv"
out_path.parent.mkdir(exist_ok=True)
out_path.write_text("\n".join(rows) + "\n")
print(f"wrote {out_path}")
