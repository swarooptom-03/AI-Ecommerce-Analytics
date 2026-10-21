"""Clean order source data into fact_orders.

Reads Data/orders_raw.csv only. Never overwrites *_raw.csv files.
Validates customer and product keys against cleaned dimensions.
Region validation is pending until dim_region exists.
"""

from pathlib import Path

import pandas as pd

SOURCE = Path("Data/orders_raw.csv")
CUSTOMERS = Path("Data/cleaned_customers.csv")
PRODUCTS = Path("Data/cleaned_products.csv")
REGIONS = Path("Data/cleaned_regions.csv")
OUTPUT = Path("Data/cleaned_orders.csv")

# Catalog vs order amounts can differ by cents of rounding.
MONEY_TOLERANCE = 0.01
VALID_DISCOUNTS = {0.0, 0.05, 0.10, 0.15, 0.20}


def fk_status(series: pd.Series, valid_ids: set[str]) -> pd.Series:
    missing = series.isna() | series.astype(str).str.strip().eq("")
    unmatched = ~missing & ~series.isin(valid_ids)
    status = pd.Series("VALID", index=series.index)
    status = status.mask(missing, "MISSING")
    status = status.mask(unmatched, "UNMATCHED")
    return status


def catalog_status(has_product: pd.Series, abs_gap: pd.Series) -> pd.Series:
    status = pd.Series("MATCH", index=abs_gap.index)
    status = status.mask(abs_gap > MONEY_TOLERANCE, "MISMATCH")
    status = status.mask(~has_product, "SKIPPED")
    return status


def main() -> None:
    df = pd.read_csv(SOURCE)
    customers = pd.read_csv(CUSTOMERS)
    products = pd.read_csv(PRODUCTS)
    input_rows = len(df)

    print("Source:", SOURCE)
    print("Input rows:", input_rows)
    print("Columns:", list(df.columns))
    print("Inferred dtypes:")
    print(df.dtypes.to_string())
    print("Missing values by column:")
    print(df.isna().sum().to_string())

    exact_dup_extra = int(df.duplicated().sum())
    id_dup_extra = int(df.duplicated(subset=["order_id"]).sum())
    print("Exact duplicate extra rows:", exact_dup_extra)
    print("Duplicate order_id extra rows:", id_dup_extra)

    conflicts = []
    for order_id, group in df.groupby("order_id", dropna=False):
        if len(group) <= 1:
            continue
        differing = [
            col for col in group.columns if group[col].nunique(dropna=False) > 1
        ]
        if differing:
            conflicts.append((order_id, differing, len(group)))
    if conflicts:
        print("CONFLICTS: same order_id with different attribute values:")
        for order_id, cols, n in conflicts:
            print(f"  {order_id}: {n} rows, differing columns {cols}")
        raise SystemExit(
            "Stopped: conflicting duplicate IDs need a justified rule before collapsing."
        )
    print(
        "Conflict check: no duplicate order_id has differing values. "
        "All ID duplicates are exact row copies, so drop_duplicates(keep='first') "
        "is deterministic."
    )

    cleaned = df.drop_duplicates(keep="first").copy()

    parsed_dates = pd.to_datetime(cleaned["order_date"], errors="coerce")
    cleaned["invalid_order_date"] = parsed_dates.isna()
    cleaned["order_date_parsed"] = parsed_dates.dt.strftime("%Y-%m-%d")
    cleaned.loc[cleaned["invalid_order_date"], "order_date_parsed"] = pd.NA
    print("Invalid order_date values:", int(cleaned["invalid_order_date"].sum()))
    print(
        "Invalid date token sample:",
        cleaned.loc[cleaned["invalid_order_date"], "order_date"].unique().tolist(),
    )

    customer_ids = set(customers["customer_id"].dropna().astype(str))
    product_ids = set(products["product_id"].dropna().astype(str))
    cleaned["customer_fk_status"] = fk_status(cleaned["customer_id"], customer_ids)
    cleaned["product_fk_status"] = fk_status(cleaned["product_id"], product_ids)

    if REGIONS.exists():
        regions = pd.read_csv(REGIONS)
        region_ids = set(regions["region_id"].dropna().astype(str))
        cleaned["region_fk_status"] = fk_status(cleaned["region_id"], region_ids)
        print("Region dimension found; region_id validated.")
    else:
        cleaned["region_fk_status"] = "PENDING"
        print("Region validation pending: Data/cleaned_regions.csv does not exist yet.")

    print("customer_fk_status:")
    print(cleaned["customer_fk_status"].value_counts().to_string())
    print("product_fk_status:")
    print(cleaned["product_fk_status"].value_counts().to_string())
    print("region_fk_status:")
    print(cleaned["region_fk_status"].value_counts().to_string())

    cleaned["is_return"] = cleaned["quantity"] < 0
    cleaned["unsigned_return_cost"] = cleaned["is_return"] & (cleaned["cost_amount"] > 0)
    print("Return rows (quantity < 0):", int(cleaned["is_return"].sum()))
    print(
        "Returns with positive cost_amount:",
        int(cleaned["unsigned_return_cost"].sum()),
    )

    # Original cost_amount and profit are kept. For returns the source stores
    # cost as a positive absolute value. cost_amount_signed uses the quantity
    # sign so returns reverse cost: -cost_amount when quantity < 0.
    cleaned["cost_amount_signed"] = cleaned["cost_amount"].where(
        ~cleaned["is_return"], -cleaned["cost_amount"]
    )

    invalid_discount = ~cleaned["discount"].isin(VALID_DISCOUNTS)
    qty_zero = cleaned["quantity"] == 0
    print("Discounts outside {0, 0.05, 0.10, 0.15, 0.20}:", int(invalid_discount.sum()))
    print("Zero quantity rows:", int(qty_zero.sum()))
    print("quantity range:", int(cleaned["quantity"].min()), "to", int(cleaned["quantity"].max()))
    print("discount unique:", sorted(cleaned["discount"].unique().tolist()))

    catalog = products[["product_id", "cost", "selling_price"]]
    merged = cleaned.merge(catalog, on="product_id", how="left", suffixes=("", "_list"))
    has_product = cleaned["product_fk_status"].eq("VALID")
    expected_sales = merged["selling_price"] * merged["quantity"] * (1 - merged["discount"])
    expected_cost_signed = merged["cost"] * merged["quantity"]
    sales_gap = (merged["sales_amount"] - expected_sales).abs()
    cost_gap = (merged["cost_amount_signed"] - expected_cost_signed).abs()
    profit_gap_raw = (merged["profit"] - (merged["sales_amount"] - merged["cost_amount"])).abs()
    profit_gap_signed = (
        merged["profit"] - (merged["sales_amount"] - merged["cost_amount_signed"])
    ).abs()

    cleaned["sales_catalog_check"] = catalog_status(has_product, sales_gap)
    cleaned["cost_catalog_check"] = catalog_status(has_product, cost_gap)
    profit_status = pd.Series("MATCH", index=cleaned.index)
    profit_status = profit_status.mask(profit_gap_raw > MONEY_TOLERANCE, "MISMATCH")
    cleaned["profit_vs_sales_minus_cost"] = profit_status

    pos = has_product & (cleaned["quantity"] > 0)
    ret = has_product & cleaned["is_return"]
    print("Positive-qty rows with a product key:", int(pos.sum()))
    print(
        "sales vs selling_price * qty * (1-discount) mismatches (positive qty):",
        int((cleaned.loc[pos, "sales_catalog_check"] == "MISMATCH").sum()),
    )
    print(
        "cost vs list_cost * qty mismatches (positive qty, signed cost):",
        int((cleaned.loc[pos, "cost_catalog_check"] == "MISMATCH").sum()),
    )
    print(
        "profit vs sales-cost mismatches (positive qty, original cost):",
        int((profit_gap_raw > MONEY_TOLERANCE)[pos].sum()),
    )
    print("Return rows with a product key:", int(ret.sum()))
    print(
        "sales catalog mismatches (returns):",
        int((cleaned.loc[ret, "sales_catalog_check"] == "MISMATCH").sum()),
    )
    print(
        "cost vs list_cost * qty (signed) mismatches (returns):",
        int((cleaned.loc[ret, "cost_catalog_check"] == "MISMATCH").sum()),
    )
    print(
        "profit vs original sales-cost mismatches (returns):",
        int((profit_gap_raw > MONEY_TOLERANCE)[ret].sum()),
    )
    print(
        "profit vs sales - cost_amount_signed mismatches (returns):",
        int((profit_gap_signed > MONEY_TOLERANCE)[ret].sum()),
    )
    print(
        "Catalog checks skipped (no product_id):",
        int((cleaned["sales_catalog_check"] == "SKIPPED").sum()),
    )

    if cleaned["order_id"].duplicated().any():
        raise SystemExit("Failed uniqueness: order_id still duplicated.")
    if cleaned["order_id"].isna().any():
        raise SystemExit("Failed: missing order_id in output.")

    original_cols = list(df.columns)
    extra_cols = [
        "order_date_parsed",
        "invalid_order_date",
        "is_return",
        "unsigned_return_cost",
        "cost_amount_signed",
        "customer_fk_status",
        "product_fk_status",
        "region_fk_status",
        "sales_catalog_check",
        "cost_catalog_check",
        "profit_vs_sales_minus_cost",
    ]
    cleaned = cleaned[original_cols + extra_cols]
    cleaned = cleaned.sort_values("order_id").reset_index(drop=True)
    cleaned.to_csv(OUTPUT, index=False)

    print("Output file:", OUTPUT)
    print("Output rows:", len(cleaned))
    print("Duplicates removed:", input_rows - len(cleaned))
    print("Unique order_id:", cleaned["order_id"].nunique())
    print("One row per order_id:", len(cleaned) == cleaned["order_id"].nunique())
    print("Output columns:", list(cleaned.columns))


if __name__ == "__main__":
    main()
