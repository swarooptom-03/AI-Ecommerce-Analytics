"""Clean product source data into dim_product.

Reads Data/products_raw.csv only. Never overwrites *_raw.csv files.
"""

from pathlib import Path

import pandas as pd

SOURCE = Path("Data/products_raw.csv")
OUTPUT = Path("Data/cleaned_products.csv")

# Map stripped, lowercased source labels to one canonical form.
# Unknown labels are title-cased after strip and still flagged if they
# fail the category/sub_category rule below.
CATEGORY_CANONICAL = {
    "clothing": "Clothing",
    "electronics": "Electronics",
    "furniture": "Furniture",
    "home & kitchen": "Home & Kitchen",
    "office supplies": "Office Supplies",
}

# Allowed pairs taken from the 88 products whose source category was
# already a canonical label. The 12 dirty-label rows are not used to
# define the catalog, and their categories are not reassigned.
ALLOWED_SUBCATEGORIES = {
    "Clothing": {"Kids", "Men", "Women"},
    "Electronics": {"Accessories", "Laptops", "Mobiles"},
    "Furniture": {"Chairs", "Storage", "Tables"},
    "Home & Kitchen": {"Appliances", "Cookware", "Decor"},
    "Office Supplies": {"Paper", "Printers", "Stationery"},
}


def standardize_category(value: str) -> str:
    stripped = str(value).strip()
    return CATEGORY_CANONICAL.get(stripped.lower(), stripped.title())


def main() -> None:
    df = pd.read_csv(SOURCE)
    input_rows = len(df)

    print("Source:", SOURCE)
    print("Input rows:", input_rows)
    print("Columns:", list(df.columns))
    print("Inferred dtypes:")
    print(df.dtypes.to_string())
    print("Missing values by column:")
    print(df.isna().sum().to_string())

    exact_dup_extra = int(df.duplicated().sum())
    id_dup_extra = int(df.duplicated(subset=["product_id"]).sum())
    print("Exact duplicate extra rows:", exact_dup_extra)
    print("Duplicate product_id extra rows:", id_dup_extra)
    print("Unique product_id in source:", df["product_id"].nunique(dropna=False))

    if id_dup_extra:
        conflicts = []
        for product_id, group in df.groupby("product_id", dropna=False):
            if len(group) <= 1:
                continue
            differing = [
                col for col in group.columns if group[col].nunique(dropna=False) > 1
            ]
            if differing:
                conflicts.append((product_id, differing, len(group)))
        if conflicts:
            print("CONFLICTS: same product_id with different attribute values:")
            for product_id, cols, n in conflicts:
                print(f"  {product_id}: {n} rows, differing columns {cols}")
            raise SystemExit(
                "Stopped: conflicting duplicate IDs need a justified rule before collapsing."
            )

    cleaned = df.drop_duplicates(keep="first").copy()
    cleaned["category"] = cleaned["category"].map(standardize_category)
    cleaned["sub_category"] = cleaned["sub_category"].astype(str).str.strip()

    labels_changed = int((df["category"].astype(str) != cleaned["category"]).sum())
    print("Category labels standardized (value changed):", labels_changed)
    print("Category values after standardization:")
    print(cleaned["category"].value_counts().to_string())

    allowed = cleaned["category"].map(ALLOWED_SUBCATEGORIES)
    combo_ok = [
        sub in allowed_set if isinstance(allowed_set, set) else False
        for sub, allowed_set in zip(cleaned["sub_category"], allowed)
    ]
    cleaned["category_review_flag"] = [
        "REVIEW" if not ok else "OK" for ok in combo_ok
    ]

    flagged = cleaned[cleaned["category_review_flag"] == "REVIEW"]
    print("Flagged category/sub_category mismatches:", len(flagged))
    if len(flagged):
        print(
            flagged[
                ["product_id", "product_name", "category", "sub_category", "category_review_flag"]
            ].to_string(index=False)
        )
        print(
            "Rule: these rows keep their standardized category; "
            "categories are not guessed from sub_category or product_name."
        )

    empty_name = int(cleaned["product_name"].astype(str).str.strip().eq("").sum())
    missing_name = int(cleaned["product_name"].isna().sum())
    missing_cost = int(cleaned["cost"].isna().sum())
    missing_price = int(cleaned["selling_price"].isna().sum())
    invalid_cost = int(((cleaned["cost"] <= 0) | cleaned["cost"].isna()).sum())
    invalid_price = int(
        ((cleaned["selling_price"] <= 0) | cleaned["selling_price"].isna()).sum()
    )
    price_below_cost = int((cleaned["selling_price"] < cleaned["cost"]).sum())

    print("Missing/blank product_name:", missing_name + empty_name)
    print("Missing cost:", missing_cost, "| missing selling_price:", missing_price)
    print("Non-positive cost:", invalid_cost, "| non-positive selling_price:", invalid_price)
    print("selling_price < cost:", price_below_cost)
    print("cost range:", float(cleaned["cost"].min()), "to", float(cleaned["cost"].max()))
    print(
        "selling_price range:",
        float(cleaned["selling_price"].min()),
        "to",
        float(cleaned["selling_price"].max()),
    )

    if cleaned["product_id"].duplicated().any():
        raise SystemExit("Failed uniqueness: product_id still duplicated.")
    if cleaned["product_id"].isna().any():
        raise SystemExit("Failed: missing product_id in output.")

    cleaned = cleaned.sort_values("product_id").reset_index(drop=True)
    cleaned.to_csv(OUTPUT, index=False)

    print("Output file:", OUTPUT)
    print("Output rows:", len(cleaned))
    print("Duplicates removed:", input_rows - len(cleaned))
    print("Unique product_id:", cleaned["product_id"].nunique())
    print("One row per product_id:", len(cleaned) == cleaned["product_id"].nunique())
    print("Output columns:", list(cleaned.columns))


if __name__ == "__main__":
    main()
