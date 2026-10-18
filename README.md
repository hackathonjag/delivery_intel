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
   free text, then search across ~50 historical projects using
   `ai_similarity()` (with TF-IDF fallback). Write ranked matches to
   `dpm_dev.mlops.similar_project_matches`.
4. **Estimates & Workflow** — Pull estimates from
   `project_estimate_summary`, compare with historical actuals,
   display role breakdowns, Azure DevOps work items, and the
   7-stage delivery lifecycle.

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
├── app.py                      # Main Streamlit application
├── app.yaml                    # Databricks App manifest
├── config.py                   # Tables, warehouse, volume paths
├── requirements.txt            # Python dependencies
├── README.md
└── utils/
    ├── __init__.py
    ├── db.py                   # Databricks SQL connection helpers
    ├── ai_search.py            # AI similarity search engine
    └── transcript_parser.py    # RAM transcript markdown parser
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

## Configuration

All table names, warehouse settings, and volume paths are centralized
in `config.py`. The SQL warehouse used is **OPM Queries**
(`902ba628be17bac8`).
