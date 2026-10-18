"""05 - Validate Vector Search indexes with sample queries.

Runs test queries against both indexes and displays results.
Also demonstrates the SQL vector_search() table-valued function
that the Streamlit app will use.

Run on a Python cluster after 04_create_indexes.py completes.
"""

from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession
import json

w = WorkspaceClient()
spark = SparkSession.builder.getOrCreate()

CATALOG = "dpm_dev"
SCHEMA = "mlops"
ENDPOINT = "dpm-project-search"

CORPUS_INDEX = f"{CATALOG}.{SCHEMA}.vs_project_corpus_idx"
INTAKE_INDEX = f"{CATALOG}.{SCHEMA}.vs_project_intakes_idx"

# ======================================================================
# Test 1: SDK query against corpus index
# ======================================================================
print("=" * 60)
print("TEST 1: SDK query - Corpus index")
print("Query: 'AI platform for delivery intelligence and forecasting'")
print("=" * 60)

results = w.vector_search_indexes.query_index(
    index_name=CORPUS_INDEX,
    columns=[
        "project_id", "project_name", "project_size",
        "line_of_business", "workitem_tags",
    ],
    query_text="AI platform for delivery intelligence and forecasting",
    num_results=5,
)

print(f"\nReturned {len(results.result.data_array)} results:\n")
for i, row in enumerate(results.result.data_array, 1):
    # Last column is the similarity score
    score = row[-1]
    print(f"  {i}. [{row[0]}] {row[1]}")
    print(f"     Size={row[2]}  LOB={row[3]}  Score={score:.4f}")
    print(f"     Tags: {str(row[4])[:80]}")
    print()


# ======================================================================
# Test 2: SDK query against intakes index with filter
# ======================================================================
print("=" * 60)
print("TEST 2: SDK query - Intakes index (historical only)")
print("Query: 'credit risk scoring real-time integration'")
print("=" * 60)

results2 = w.vector_search_indexes.query_index(
    index_name=INTAKE_INDEX,
    columns=[
        "project_id", "project_name",
        "estimated_complexity", "line_of_business",
    ],
    query_text="credit risk scoring real-time integration",
    num_results=5,
    filters="project_id LIKE 'HIST-%'",
)

print(f"\nReturned {len(results2.result.data_array)} results:\n")
for i, row in enumerate(results2.result.data_array, 1):
    score = row[-1]
    print(f"  {i}. [{row[0]}] {row[1]}  (complexity={row[2]}, LOB={row[3]}, score={score:.4f})")


# ======================================================================
# Test 3: SQL vector_search() table-valued function
#         This is what the Streamlit app can call via SQL warehouse.
# ======================================================================
print("\n" + "=" * 60)
print("TEST 3: SQL vector_search() - usable from SQL warehouse")
print("=" * 60)

df = spark.sql(f"""
SELECT *
FROM VECTOR_SEARCH(
    index => '{CORPUS_INDEX}',
    query => 'AI platform for delivery intelligence and forecasting',
    num_results => 5
)
""")
df.show(truncate=False)


# ======================================================================
# Test 4: Hybrid search (semantic + keyword)
# ======================================================================
print("=" * 60)
print("TEST 4: Hybrid search (semantic + keyword)")
print("Query: 'servicenow generative-ai integration'")
print("=" * 60)

results3 = w.vector_search_indexes.query_index(
    index_name=CORPUS_INDEX,
    columns=[
        "project_id", "project_name", "workitem_tags",
    ],
    query_text="servicenow generative-ai integration",
    query_type="HYBRID",
    num_results=5,
)

print(f"\nReturned {len(results3.result.data_array)} results:\n")
for i, row in enumerate(results3.result.data_array, 1):
    score = row[-1]
    print(f"  {i}. [{row[0]}] {row[1]}  score={score:.4f}")
    print(f"     Tags: {str(row[2])[:100]}")
    print()

print("\nAll validation tests complete.")
