"""01 - Create Vector Search Endpoint.

Run this notebook cell-by-cell on a Python-capable cluster in the
target workspace.  It creates a single Storage-Optimized endpoint
that will host all project-search indexes.

Prerequisites
-------------
* Workspace must have Vector Search enabled (Premium / Enterprise).
* The running user needs workspace-level permissions to create
  Vector Search endpoints.
* databricks-sdk >= 0.20.0  (pre-installed on DBR 14.3+)
"""

# ---------- configuration ----------
ENDPOINT_NAME = "dpm-project-search"
# Storage-Optimized: 7x lower cost, 1B+ vector capacity, ~300ms latency.
# Switch to "STANDARD" if you need <50ms latency.
ENDPOINT_TYPE = "STORAGE_OPTIMIZED"

# ---------- create endpoint ----------
from databricks.sdk import WorkspaceClient
import time

w = WorkspaceClient()

# Check if endpoint already exists
existing = {ep.name for ep in w.vector_search_endpoints.list_endpoints()}
if ENDPOINT_NAME in existing:
    print(f"Endpoint '{ENDPOINT_NAME}' already exists.")
else:
    print(f"Creating {ENDPOINT_TYPE} endpoint '{ENDPOINT_NAME}'...")
    w.vector_search_endpoints.create_endpoint(
        name=ENDPOINT_NAME,
        endpoint_type=ENDPOINT_TYPE,
    )
    print("Creation initiated.")

# ---------- wait for ONLINE ----------
print("Waiting for endpoint to reach ONLINE state...")
for _ in range(60):  # up to 10 minutes
    ep = w.vector_search_endpoints.get_endpoint(endpoint_name=ENDPOINT_NAME)
    state = ep.endpoint_status.state.value if ep.endpoint_status else "UNKNOWN"
    print(f"  status: {state}")
    if state == "ONLINE":
        print(f"\nEndpoint '{ENDPOINT_NAME}' is ONLINE and ready.")
        break
    time.sleep(10)
else:
    print(
        f"\nEndpoint did not reach ONLINE within 10 min. "
        f"Check the Vector Search UI and re-run the wait loop."
    )
