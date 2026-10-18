"""04 - Create Vector Search Delta Sync Indexes.

Creates two managed-embedding indexes on the `dpm-project-search` endpoint:

  Index                              | Source table              | Embedding column   | Use case
  -----------------------------------|---------------------------|--------------------|------------------------------
  dpm_dev.mlops.vs_project_corpus_idx| project_search_corpus     | search_text        | Primary: full-context search
  dpm_dev.mlops.vs_project_intakes_idx| project_intakes           | Combined text expr | Lightweight: intake-only

Both use `databricks-gte-large-en` (1024-dim, 8192-token context).

Prerequisites
-------------
* Run 01, 02, 03 first.
* Endpoint `dpm-project-search` must be ONLINE.
* User needs USE CATALOG + USE SCHEMA + CREATE TABLE on dpm_dev.mlops,
  AND CAN_USE on the Vector Search endpoint (separate permission).
"""

from databricks.sdk import WorkspaceClient
import time

w = WorkspaceClient()

CATALOG = "dpm_dev"
SCHEMA = "mlops"
ENDPOINT = "dpm-project-search"
EMBEDDING_MODEL = "databricks-gte-large-en"

# ======================================================================
# Index definitions
# ======================================================================
INDEXES = [
    {
        "name": f"{CATALOG}.{SCHEMA}.vs_project_corpus_idx",
        "source_table": f"{CATALOG}.{SCHEMA}.project_search_corpus",
        "primary_key": "project_id",
        "embedding_column": "search_text",
        "sync_columns": [
            "project_id", "project_name", "project_source",
            "project_size", "line_of_business",
            "search_text", "workitem_tags", "workitem_count",
        ],
        "description": "Full-context corpus (intake + planview + tags + transcript)",
    },
    {
        "name": f"{CATALOG}.{SCHEMA}.vs_project_intakes_idx",
        "source_table": f"{CATALOG}.{SCHEMA}.project_intakes",
        "primary_key": "project_id",
        "embedding_column": "problem_statement_and_desired_outcome",
        "sync_columns": [
            "project_id", "project_name",
            "problem_statement_and_desired_outcome",
            "overall_scope", "affected_systems",
            "estimated_complexity", "line_of_business",
            "request_category",
        ],
        "description": "Intake-only index on problem statement",
    },
]


# ======================================================================
# Create each index
# ======================================================================
def create_index(idx_def: dict) -> None:
    name = idx_def["name"]
    print(f"\n{'='*60}")
    print(f"Creating index: {name}")
    print(f"  Source:    {idx_def['source_table']}")
    print(f"  Embed on:  {idx_def['embedding_column']}")
    print(f"  Model:     {EMBEDDING_MODEL}")
    print(f"  Endpoint:  {ENDPOINT}")

    # Check if it already exists
    try:
        existing = w.vector_search_indexes.get_index(index_name=name)
        print(f"  Index already exists (status: {existing.status}).")
        return
    except Exception:
        pass  # Does not exist yet

    w.vector_search_indexes.create_index(
        name=name,
        endpoint_name=ENDPOINT,
        primary_key=idx_def["primary_key"],
        index_type="DELTA_SYNC",
        delta_sync_index_spec={
            "source_table": idx_def["source_table"],
            "pipeline_type": "TRIGGERED",
            "embedding_source_columns": [
                {
                    "name": idx_def["embedding_column"],
                    "embedding_model_endpoint_name": EMBEDDING_MODEL,
                }
            ],
            "columns_to_sync": idx_def["sync_columns"],
        },
    )
    print("  Creation initiated.")


for idx in INDEXES:
    create_index(idx)


# ======================================================================
# Trigger initial sync and wait
# ======================================================================
print("\n" + "="*60)
print("Triggering initial sync for all indexes...")

for idx in INDEXES:
    name = idx["name"]
    try:
        w.vector_search_indexes.sync_index(index_name=name)
        print(f"  Sync triggered: {name}")
    except Exception as e:
        print(f"  Sync trigger for {name}: {e}")

print("\nWaiting for indexes to become ONLINE...")
for _ in range(90):  # up to 15 minutes
    all_online = True
    for idx in INDEXES:
        name = idx["name"]
        try:
            status = w.vector_search_indexes.get_index(index_name=name)
            state = status.status.ready if status.status else False
            msg = status.status.message if status.status else "unknown"
            print(f"  {name}: ready={state}  ({msg})")
            if not state:
                all_online = False
        except Exception as e:
            print(f"  {name}: {e}")
            all_online = False
    if all_online:
        print("\nAll indexes are ONLINE and synced.")
        break
    time.sleep(10)
else:
    print("\nSome indexes not yet ready. Check the Vector Search UI.")

print("\nDone.")
