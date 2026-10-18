# Project Intake Workflow — Databricks Streamlit App

A prototype Streamlit application that processes new IT project intakes
through a 4-step workflow backed by the **IT Project and Workforce
Management** Genie Agent tables in `dpm_dev.mlops`.

## Features

1. **Intake Details** — View project metadata, estimate summary, and
   resource assignments.
2. **RAM Transcript** — Load a Resource Allocation Meeting transcript
   from the UC Volume (or paste one), parse participants, scope,
   estimates, and action items to enrich the search context.
3. **AI Similarity Search** — Combine intake fields + transcript +
   free text, then search across ~50 historical projects. Three-tier
   search cascade (`auto` mode): **Vector Search** →
   `ai_similarity()` → TF-IDF. Write ranked matches to
   `dpm_dev.mlops.similar_project_matches`.
4. **Estimates & Workflow** — Pull estimates from
   `project_estimate_summary`, compare with historical actuals,
   display role breakdowns, Azure DevOps work items, and the
   7-stage delivery lifecycle:
   1. **Estimate** — status, P50/P80 hours, confidence, duration
   2. **Capacity** — resource assignment conflicts
   3. **Commit** — approval gate completion
   4. **Sync** — team size and planned hours
   5. **Operational Block** — open gates and pending change requests
   6. **Variance** — actual vs P50 estimate drift
   7. **Re-plan** — closest historical match for re-baselining

## Quick Start

### As a Databricks App

```bash
# From the prototype/ folder
databricks apps deploy project-intake-workflow --source-code-path .
```

The `app.yaml` manifest configures the Streamlit command and the
SQL warehouse HTTP path.

### Local / Notebook

Set these environment variables before running:

```bash
export DATABRICKS_SERVER_HOSTNAME="<your-workspace>.azuredatabricks.net"
export DATABRICKS_TOKEN="dapi..."
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/902ba628be17bac8"
streamlit run app.py
```

## Repository Layout

```
prototype/
├── app.py                      # Main Streamlit application (4 tabs)
├── app.yaml                    # Databricks App deployment manifest
├── config.py                   # Warehouse, catalog/schema, table FQNs, volume paths
├── requirements.txt            # Python dependencies
├── README.md
├── utils/
│   ├── __init__.py
│   ├── db.py                   # Databricks SQL connection + query helpers
│   ├── ai_search.py            # 3-tier search: Vector Search → ai_similarity → TF-IDF
│   └── transcript_parser.py    # RAM transcript markdown parser
└── scripts/                    # Vector Search setup (run on target workspace)
    ├── 01_create_endpoint.py   # Create Storage-Optimized VS endpoint
    ├── 02_prepare_source_tables.py  # Enable CDF + PK constraints
    ├── 03_build_search_corpus.py    # Build denormalized corpus table
    ├── 04_create_indexes.py    # Create Delta Sync managed indexes
    └── 05_validate_search.py   # SDK, SQL VECTOR_SEARCH(), Hybrid tests
```

## Key Tables

| Table | Purpose |
|---|---|
| `project_intakes` | Intake form fields (scope, risks, dependencies) |
| `project_estimate_summary` | P50/P80 hours, duration, confidence |
| `project_role_estimates` | Per-role effort breakdown |
| `devops_workitems_details` | Epics, Features, Stories, Tasks (join on `prjnumber`) |
| `similar_project_matches` | Ranked historical matches (write target) |
| `project_resource_assignments` | Named resource allocations |
| `project_approval_dependencies` | Approval gates |
| `planview_odata_project_dimension` | Planview portfolio data (join via `work_id`) |

## Example Project

* **ID:** `INTAKE-2026-001`
* **Name:** AI-Powered Delivery Intelligence Platform
* **Starter ROM:** 5,016 h (P50) / 6,272 h (P80) over 36 weeks
* **Top match:** HIST-024 AI-Assisted Customer Support (47.2% similarity)

## RAM Transcripts

Historical transcripts are stored at:

```
/Volumes/dpm_dev/mlops/test/delivery/
  generated_delivery_intelligence_data/ram_transcripts/
```

~50 files in markdown format (`HIST-001_*.md` through `HIST-050_*.md`).

## Vector Search Index Strategy

### Candidate Fields

| Source Table | Embedding Candidate Columns | Join Key | Notes |
|---|---|---|---|
| `project_intakes` | `problem_statement_and_desired_outcome`, `overall_scope`, `affected_systems`, `business_strategy`, `known_business_risks`, `known_business_dependencies` | `project_id` | Richest free-text; ~50 HIST-* rows + active intakes |
| `planview_odata_project_dimension` | `project_description`, `known_risks_constraints_dependencies` | `work_id` (= project_id) | Adds portfolio-level context |
| `devops_workitems_details` | `title`, `description`, `tags`, `acceptancecriteria` | `prjnumber` (= project_id) | Many rows per project; aggregate tags |
| RAM transcripts (UC Volume) | Full markdown text per meeting | Filename prefix = project_id | ~50 files; loaded into Delta by script 03 |

### Architecture

A **denormalized corpus table** (`dpm_dev.mlops.project_search_corpus`) joins
all four sources into a single `search_text` column per project, capped at
8,000 chars for the `databricks-gte-large-en` (1024-dim, 8192-token) context
window.

### Indexes

| Index | Source Table | Embedding Column | Type | Use Case |
|---|---|---|---|---|
| `vs_project_corpus_idx` | `project_search_corpus` | `search_text` | Delta Sync / Managed | **Primary** — full-context (intake + planview + tags + transcript) |
| `vs_project_intakes_idx` | `project_intakes` | `problem_statement_and_desired_outcome` | Delta Sync / Managed | Lightweight — intake-only for fast queries |

### Infrastructure

* **Endpoint:** `dpm-project-search` (Storage-Optimized, ~300ms latency, 7x lower cost)
* **Embedding model:** `databricks-gte-large-en` (1024 dimensions)
* **Sync mode:** TRIGGERED (call `sync_index()` after corpus rebuild)

### Setup Scripts

Run these in order on the **target workspace** (the current workspace does
not permit Vector Search index creation):

```
scripts/01_create_endpoint.py       ← Creates the VS endpoint, waits for ONLINE
scripts/02_prepare_source_tables.py ← Enables CDF + adds PK constraints
scripts/03_build_search_corpus.py   ← Builds denormalized corpus table from 4 sources
scripts/04_create_indexes.py        ← Creates both Delta Sync indexes
scripts/05_validate_search.py       ← SDK, SQL VECTOR_SEARCH(), Hybrid search tests
```

### App Integration

`utils/ai_search.py` cascades through three methods in `auto` mode:

1. **vector_search** — `VECTOR_SEARCH()` SQL TVF against `vs_project_corpus_idx`
2. **ai_similarity** — Databricks AI Functions SQL scalar (no index needed)
3. **tfidf** — scikit-learn fallback (no infrastructure required)

The sidebar dropdown lets users force a specific method or use `auto`.

## Configuration

All table names, warehouse settings, and volume paths are centralized
in `config.py`. The SQL warehouse used is **OPM Queries**
(`902ba628be17bac8`).
