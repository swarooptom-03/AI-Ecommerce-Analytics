import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "Data"

# Read cleaned orders
orders = pd.read_csv(DATA_DIR / "cleaned_orders.csv")

# Parse valid order dates; invalid dates remain excluded from the date dimension
dates = pd.to_datetime(
    orders["order_date_parsed"],
    errors="coerce"
).dropna().drop_duplicates().sort_values()

# Build date dimension
date_dim = pd.DataFrame({"date": dates})

date_dim["date_key"] = date_dim["date"].dt.strftime("%Y%m%d").astype("int64")
date_dim["day"] = date_dim["date"].dt.day
date_dim["month"] = date_dim["date"].dt.month
date_dim["month_name"] = date_dim["date"].dt.month_name()
date_dim["quarter"] = "Q" + date_dim["date"].dt.quarter.astype(str)
date_dim["year"] = date_dim["date"].dt.year

# Put key columns first
date_dim = date_dim[
    ["date_key", "date", "day", "month", "month_name", "quarter", "year"]
]

# Save date dimension
output_file = DATA_DIR / "dim_date.csv"
date_dim.to_csv(output_file, index=False)

print("Valid order dates:", dates.nunique())
print("Date dimension rows:", len(date_dim))
print("Date range:", dates.min(), "to", dates.max())
print("Duplicate date keys:", date_dim["date_key"].duplicated().sum())
print("Saved to:", output_file)