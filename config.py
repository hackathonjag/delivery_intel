"""Configuration for the Project Intake Workflow Streamlit App."""
import os

# ---------------------------------------------------------------------------
# Databricks SQL Warehouse  ("OPM Queries")
# ---------------------------------------------------------------------------
WAREHOUSE_ID = "902ba628be17bac8"
WAREHOUSE_HTTP_PATH = os.getenv(
    "DATABRICKS_HTTP_PATH",
    f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
)

# ---------------------------------------------------------------------------
# Unity Catalog location
# ---------------------------------------------------------------------------
CATALOG = "dpm_dev"
SCHEMA = "mlops"

def _fqn(table: str) -> str:
    return f"{CATALOG}.{SCHEMA}.{table}"

# Core tables
TABLE_INTAKES = _fqn("project_intakes")
TABLE_ESTIMATES = _fqn("project_estimate_summary")
TABLE_ROLE_ESTIMATES = _fqn("project_role_estimates")
TABLE_WORKITEMS = _fqn("devops_workitems_details")
TABLE_MATCHES = _fqn("similar_project_matches")
TABLE_PLANVIEW = _fqn("planview_odata_project_dimension")
TABLE_ASSIGNMENTS = _fqn("project_resource_assignments")
TABLE_APPROVALS = _fqn("project_approval_dependencies")
TABLE_CAPACITY = _fqn("workforce_capacity_weekly")

# RAM transcripts UC Volume
TRANSCRIPT_VOLUME = (
    "/Volumes/dpm_dev/mlops/test/delivery/"
    "generated_delivery_intelligence_data/ram_transcripts"
)

# Example project (pre-populated in the UI)
DEFAULT_PROJECT_ID = "INTAKE-2026-001"
DEFAULT_PROJECT_NAME = "AI-Powered Delivery Intelligence Platform"
