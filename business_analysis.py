import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "Data"

# Load the fact table and dimensions
fact = pd.read_csv(DATA_DIR / "fact_orders.csv")
products = pd.read_csv(DATA_DIR / "dim_product.csv")
regions = pd.read_csv(DATA_DIR / "dim_region.csv")
dates = pd.read_csv(DATA_DIR / "dim_date.csv")

# Convert numeric columns
numeric_cols = ["quantity", "sales_amount", "cost_amount", "profit"]
for col in numeric_cols:
    fact[col] = pd.to_numeric(fact[col], errors="coerce")

fact["order_date_parsed"] = pd.to_datetime(
    fact["order_date_parsed"], errors="coerce"
)

# Overall KPIs
valid_dates = fact["order_date_parsed"].notna()
valid_sales = fact["sales_amount"].notna()

total_orders = fact["order_id"].nunique()
total_revenue = fact.loc[valid_sales, "sales_amount"].sum()
total_profit = fact.loc[valid_sales, "profit"].sum()
total_quantity = fact["quantity"].sum()

profit_margin = (
    total_profit / total_revenue * 100
    if total_revenue != 0 else 0
)

print("\n========== OVERALL KPIs ==========")
print(f"Unique orders: {total_orders:,}")
print(f"Total revenue: ₹{total_revenue:,.2f}")
print(f"Total profit: ₹{total_profit:,.2f}")
print(f"Overall profit margin: {profit_margin:.2f}%")
print(f"Total quantity (including returns): {total_quantity:,}")
print(f"Orders with valid dates: {valid_dates.sum():,}")
print(f"Orders with invalid dates: {(~valid_dates).sum():,}")

# Join product details
analysis = fact.merge(
    products[["product_key", "product_name", "category", "sub_category"]],
    on="product_key",
    how="left",
    validate="many_to_one"
)

# Join region details
analysis = analysis.merge(
    regions[["region_key", "state", "city", "region"]],
    on="region_key",
    how="left",
    validate="many_to_one"
)

# Revenue and profit by category
category_summary = (
    analysis.groupby("category", dropna=False)
    .agg(
        revenue=("sales_amount", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique")
    )
    .sort_values("revenue", ascending=False)
)

category_summary["profit_margin_pct"] = (
    category_summary["profit"] / category_summary["revenue"] * 100
)

print("\n========== CATEGORY PERFORMANCE ==========")
print(category_summary.round(2).to_string())

# Regional performance
region_summary = (
    analysis.groupby("region", dropna=False)
    .agg(
        revenue=("sales_amount", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique")
    )
    .sort_values("profit", ascending=False)
)

region_summary["profit_margin_pct"] = (
    region_summary["profit"] / region_summary["revenue"] * 100
)

print("\n========== REGIONAL PERFORMANCE ==========")
print(region_summary.round(2).to_string())

# Monthly trends: only rows with valid order dates
monthly = (
    analysis.loc[analysis["order_date_parsed"].notna()]
    .assign(month=lambda x: x["order_date_parsed"].dt.to_period("M").astype(str))
    .groupby("month")
    .agg(
        revenue=("sales_amount", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique")
    )
    .reset_index()
)

print("\n========== MONTHLY PERFORMANCE (LATEST 12 MONTHS) ==========")
print(monthly.tail(12).round(2).to_string(index=False))

# Top 10 products by revenue
product_summary = (
    analysis.groupby(["product_name", "category"], dropna=False)
    .agg(
        revenue=("sales_amount", "sum"),
        profit=("profit", "sum"),
        quantity=("quantity", "sum")
    )
    .sort_values("revenue", ascending=False)
    .head(10)
)

print("\n========== TOP 10 PRODUCTS BY REVENUE ==========")
print(product_summary.round(2).to_string())

# Save analysis outputs for the dashboard
category_summary.reset_index().to_csv(
    DATA_DIR / "category_analysis.csv", index=False
)
region_summary.reset_index().to_csv(
    DATA_DIR / "region_analysis.csv", index=False
)
monthly.to_csv(DATA_DIR / "monthly_analysis.csv", index=False)
product_summary.reset_index().to_csv(
    DATA_DIR / "product_analysis.csv", index=False
)

print("\nAnalysis CSVs saved in Data/")