import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "Data"

# Load cleaned datasets
orders = pd.read_csv(DATA_DIR / "cleaned_orders.csv")
customers = pd.read_csv(DATA_DIR / "cleaned_customers.csv")
products = pd.read_csv(DATA_DIR / "cleaned_products.csv")
regions = pd.read_csv(DATA_DIR / "cleaned_regions.csv")
dates = pd.read_csv(DATA_DIR / "dim_date.csv")

print("Building star schema...")

# Preserve original order rows and columns
fact = orders.copy()

# Normalize IDs for reliable matching
for df, col in [
    (fact, "customer_id"),
    (fact, "product_id"),
    (fact, "region_id"),
]:
    df[col] = df[col].astype("string").str.strip()

for df, col in [
    (customers, "customer_id"),
    (products, "product_id"),
    (regions, "region_id"),
]:
    df[col] = df[col].astype("string").str.strip()

# Add surrogate dimension keys
customers["customer_key"] = range(1, len(customers) + 1)
products["product_key"] = range(1, len(products) + 1)
regions["region_key"] = range(1, len(regions) + 1)

# Map natural IDs to dimension keys
fact = fact.merge(
    customers[["customer_id", "customer_key"]],
    on="customer_id",
    how="left",
    validate="many_to_one",
)

fact = fact.merge(
    products[["product_id", "product_key"]],
    on="product_id",
    how="left",
    validate="many_to_one",
)

fact = fact.merge(
    regions[["region_id", "region_key"]],
    on="region_id",
    how="left",
    validate="many_to_one",
)

# Create the order date key
fact["order_date_parsed"] = pd.to_datetime(
    fact["order_date_parsed"], errors="coerce"
)

dates["date"] = pd.to_datetime(dates["date"], errors="coerce")
dates["date_key"] = dates["date_key"].astype("Int64")

date_key_map = dates.set_index("date")["date_key"]

fact["date_key"] = fact["order_date_parsed"].map(date_key_map).astype("Int64")

# Save fact table
fact_file = DATA_DIR / "fact_orders.csv"
fact.to_csv(fact_file, index=False)

# Save dimensions with surrogate keys
customers.to_csv(DATA_DIR / "dim_customer.csv", index=False)
products.to_csv(DATA_DIR / "dim_product.csv", index=False)
regions.to_csv(DATA_DIR / "dim_region.csv", index=False)

# Validation report
print("\n--- STAR SCHEMA VALIDATION ---")
print("Fact rows:", len(fact))
print("Unique order IDs:", fact["order_id"].nunique())
print("Customer keys missing:", fact["customer_key"].isna().sum())
print("Product keys missing:", fact["product_key"].isna().sum())
print("Region keys missing:", fact["region_key"].isna().sum())
print("Date keys missing:", fact["date_key"].isna().sum())
print("Duplicate order IDs:", fact["order_id"].duplicated().sum())
print("\nSaved fact table:", fact_file)
print("Saved dimension tables: dim_customer.csv, dim_product.csv, dim_region.csv")