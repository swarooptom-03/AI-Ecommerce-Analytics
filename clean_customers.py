"""Clean customer source data into dim_customer.

Reads Data/customers_raw.csv only. Never writes back to Data/.
"""

from pathlib import Path

import pandas as pd

# Source stays in Data/. Cleaned output is requested at data/.
# On this Mac the disk is case-insensitive, so Data/ and data/ are the
# same folder. The script still uses the lowercase output path.
SOURCE = Path("Data/customers_raw.csv")
OUTPUT_DIR = Path("data")
OUTPUT = OUTPUT_DIR / "cleaned_customers.csv"

# Reasonable adult-age bounds for this e-commerce set. Values outside
# are flagged, not silently rewritten.
AGE_MIN = 0
AGE_MAX = 120


def main() -> None:
    df = pd.read_csv(SOURCE)
    input_rows = len(df)
    input_cols = list(df.columns)

    print("Source:", SOURCE)
    print("Input rows:", input_rows)
    print("Columns:", input_cols)
    print("Inferred dtypes:")
    print(df.dtypes.to_string())
    print("Missing values by column:")
    print(df.isna().sum().to_string())

    exact_dup_extra = int(df.duplicated().sum())
    id_dup_extra = int(df.duplicated(subset=["customer_id"]).sum())
    dup_ids = sorted(
        df.loc[df.duplicated("customer_id", keep=False), "customer_id"].unique().tolist()
    )

    print("Exact duplicate extra rows:", exact_dup_extra)
    print("Duplicate customer_id extra rows:", id_dup_extra)
    print("Duplicate customer_id values:", dup_ids)

    conflicts = []
    for customer_id, group in df.groupby("customer_id", dropna=False):
        if len(group) <= 1:
            continue
        differing = [
            col for col in group.columns if group[col].nunique(dropna=False) > 1
        ]
        if differing:
            conflicts.append((customer_id, differing, len(group)))

    if conflicts:
        print("CONFLICTS: same customer_id with different attribute values:")
        for customer_id, cols, n in conflicts:
            print(f"  {customer_id}: {n} rows, differing columns {cols}")
        raise SystemExit(
            "Stopped: conflicting duplicate IDs need a justified rule before collapsing."
        )

    print(
        "Conflict check: no duplicate customer_id has differing values. "
        "All ID duplicates are exact row copies, so drop_duplicates(keep='first') "
        "is deterministic and does not pick among competing records."
    )

    cleaned = df.drop_duplicates(keep="first").copy()

    parsed_dates = pd.to_datetime(cleaned["signup_date"], errors="coerce")
    invalid_dates = int(parsed_dates.isna().sum())
    cleaned["signup_date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    age = cleaned["age"]
    invalid_age = int(((age < AGE_MIN) | (age > AGE_MAX) | age.isna()).sum())
    print("Age range after dedupe:", int(age.min()), "to", int(age.max()))
    print("Invalid ages (outside 0-120 or missing):", invalid_age)
    print("Invalid signup_date values (unparseable):", invalid_dates)

    if cleaned["customer_id"].duplicated().any():
        raise SystemExit("Failed uniqueness: customer_id still duplicated.")
    if cleaned["customer_id"].isna().any():
        raise SystemExit("Failed: missing customer_id in output.")

    cleaned = cleaned.sort_values("customer_id").reset_index(drop=True)

    OUTPUT_DIR.mkdir(exist_ok=True)
    cleaned.to_csv(OUTPUT, index=False)

    print("Output file:", OUTPUT)
    print("Output rows:", len(cleaned))
    print("Duplicates removed:", input_rows - len(cleaned))
    print("Unique customer_id:", cleaned["customer_id"].nunique())
    print("One row per customer_id:", len(cleaned) == cleaned["customer_id"].nunique())


if __name__ == "__main__":
    main()
