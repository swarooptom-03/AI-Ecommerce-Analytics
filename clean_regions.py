import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "Data"

raw_file = DATA_DIR / "regions_raw.csv"
output_file = DATA_DIR / "cleaned_regions.csv"

# Read raw data
df = pd.read_csv(raw_file)

print("Input rows:", len(df))
print("\nMissing values before cleaning:")
print(df.isna().sum())

# Remove exact duplicate rows only
df = df.drop_duplicates().copy()

# Standardize whitespace in text columns
for column in df.select_dtypes(include="object").columns:
    df[column] = df[column].str.strip()

# Check required columns
required_columns = ["region_id", "state", "city", "region"]
missing_columns = [c for c in required_columns if c not in df.columns]

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

# Flag missing or duplicate region IDs
df["region_review_flag"] = "OK"

missing_values = df[required_columns].isna().any(axis=1)
df.loc[missing_values, "region_review_flag"] = "REVIEW_MISSING_VALUES"

duplicate_ids = df["region_id"].notna() & df["region_id"].duplicated(keep=False)
df.loc[duplicate_ids, "region_review_flag"] = "REVIEW_DUPLICATE_REGION_ID"

# Save without modifying the raw file
df.to_csv(output_file, index=False)

print("\nOutput rows:", len(df))
print("Exact duplicate rows removed:", "check the input/output row counts")
print("Duplicate region IDs:", df["region_id"].duplicated().sum())
print("Rows requiring review:", (df["region_review_flag"] != "OK").sum())
print("\nRegion counts:")
print(df["region"].value_counts(dropna=False))
print("\nSaved to:", output_file)