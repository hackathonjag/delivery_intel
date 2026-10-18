"""02 - Prepare source tables for Vector Search Delta Sync.

Delta Sync indexes require:
  1. Change Data Feed (CDF) enabled on each source table.
  2. A declared Unity Catalog PRIMARY KEY constraint.

Run on a Python cluster that has write access to dpm_dev.mlops.
"""

CATALOG = "dpm_dev"
SCHEMA = "mlops"

# ======================================================================
# Tables and their natural primary-key columns
# ======================================================================
TABLE_PK_MAP = {
    # ---- tables that feed the search corpus ----
    "project_intakes":                 "project_id",
    "project_estimate_summary":        "project_id",
    "planview_odata_project_dimension": "id",
    "devops_workitems_details":         "workitem_id",
    # ---- the corpus table itself (created in step 03) ----
    "project_search_corpus":           "project_id",
}

# ======================================================================
# Enable CDF + add PK
# ======================================================================
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

for table, pk_col in TABLE_PK_MAP.items():
    fqn = f"{CATALOG}.{SCHEMA}.{table}"
    print(f"\n--- {fqn} ---")

    # Check if table exists (corpus table won't exist yet)
    try:
        spark.sql(f"DESCRIBE TABLE {fqn}")
    except Exception:
        print(f"  Table does not exist yet; skipping (will be created in step 03).")
        continue

    # 1. Enable Change Data Feed
    try:
        spark.sql(
            f"ALTER TABLE {fqn} "
            f"SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
        )
        print(f"  CDF enabled.")
    except Exception as e:
        print(f"  CDF: {e}")

    # 2. Declare primary key (NOT ENFORCED — metadata only for VS)
    #    Drop existing constraint first if it exists.
    constraint_name = f"pk_{table}"
    try:
        spark.sql(f"ALTER TABLE {fqn} DROP CONSTRAINT IF EXISTS {constraint_name}")
        spark.sql(
            f"ALTER TABLE {fqn} ADD CONSTRAINT {constraint_name} "
            f"PRIMARY KEY ({pk_col}) NOT ENFORCED"
        )
        print(f"  PK constraint '{constraint_name}' on ({pk_col}).")
    except Exception as e:
        print(f"  PK: {e}")

print("\nSource tables prepared.")
