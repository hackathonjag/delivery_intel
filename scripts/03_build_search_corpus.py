"""03 - Build a denormalized search corpus table.

Creates `dpm_dev.mlops.project_search_corpus` by joining text fields
from four sources into a single `search_text` column optimised for
vector embedding:

  Source                         | Fields contributed
  -------------------------------|--------------------------------------------
  project_intakes                | problem_statement, scope, systems, strategy,
                                 | risks, dependencies, complexity, category,
                                 | line_of_business
  planview_odata_project_dimension| project_description, risks_constraints
  devops_workitems_details       | aggregated tags per project
  RAM transcripts (UC Volume)    | full meeting text per project

The table has CDF enabled + PK so it can serve as a Delta Sync source.
Re-run this script whenever source data changes; the table will be
replaced (CREATE OR REPLACE).

Run on a Python cluster with access to dpm_dev.mlops.
"""

from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

CATALOG = "dpm_dev"
SCHEMA = "mlops"
CORPUS_TABLE = f"{CATALOG}.{SCHEMA}.project_search_corpus"
TRANSCRIPT_VOLUME = (
    "/Volumes/dpm_dev/mlops/test/delivery/"
    "generated_delivery_intelligence_data/ram_transcripts"
)

# ======================================================================
# Step A: Load RAM transcripts from the UC Volume into a temp view.
#         Each file becomes one row keyed by the HIST-nnn prefix.
# ======================================================================
print("Loading RAM transcripts from volume...")

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW _ram_raw AS
SELECT
    _metadata.file_name                          AS file_name,
    REGEXP_EXTRACT(_metadata.file_name,
                   '(HIST-\\d+|INTAKE-\\d+-\\d+)', 0) AS project_id,
    COLLECT_LIST(value)                           AS lines
FROM read_files('{TRANSCRIPT_VOLUME}/', format => 'text')
GROUP BY _metadata.file_name
""")

spark.sql("""
CREATE OR REPLACE TEMP VIEW _ram_transcripts AS
SELECT
    project_id,
    CONCAT_WS('\n', lines) AS transcript_text
FROM _ram_raw
WHERE project_id IS NOT NULL AND project_id <> ''
""")

ram_count = spark.sql("SELECT COUNT(*) AS n FROM _ram_transcripts").collect()[0]["n"]
print(f"  {ram_count} transcripts loaded.")

# ======================================================================
# Step B: Aggregate DevOps work-item tags per project.
# ======================================================================
print("Aggregating DevOps tags...")

spark.sql(f"""
CREATE OR REPLACE TEMP VIEW _workitem_tags AS
SELECT
    prjnumber                              AS project_id,
    CONCAT_WS('; ',
        COLLECT_SET(tags))                 AS all_tags,
    CONCAT_WS(' ',
        COLLECT_SET(title))                AS all_titles,
    COUNT(*)                               AS workitem_count
FROM {CATALOG}.{SCHEMA}.devops_workitems_details
WHERE prjnumber IS NOT NULL
GROUP BY prjnumber
""")

# ======================================================================
# Step C: Build the corpus table.
# ======================================================================
print("Building search corpus...")

spark.sql(f"""
CREATE OR REPLACE TABLE {CORPUS_TABLE}
(
    project_id          STRING  NOT NULL,
    project_name        STRING,
    project_source      STRING  COMMENT 'intake | planview | both',
    project_size        STRING,
    line_of_business    STRING,
    search_text         STRING  COMMENT 'Combined text for vector embedding',
    transcript_text     STRING  COMMENT 'Raw RAM transcript (if available)',
    workitem_tags       STRING  COMMENT 'Aggregated DevOps tags',
    workitem_count      INT,
    CONSTRAINT pk_project_search_corpus PRIMARY KEY (project_id) NOT ENFORCED
)
USING DELTA
TBLPROPERTIES (
    delta.enableChangeDataFeed = true
)
COMMENT 'Denormalized search corpus for Vector Search similarity matching.'
""")

spark.sql(f"""
INSERT OVERWRITE {CORPUS_TABLE}
WITH intake AS (
    SELECT
        project_id,
        project_name,
        line_of_business,
        estimated_complexity        AS project_size,
        CONCAT_WS(' | ',
            COALESCE(project_name, ''),
            COALESCE(problem_statement_and_desired_outcome, ''),
            COALESCE(overall_scope, ''),
            COALESCE(affected_systems, ''),
            COALESCE(business_strategy, ''),
            COALESCE(request_category, ''),
            COALESCE(estimated_complexity, ''),
            COALESCE(known_business_risks, ''),
            COALESCE(known_business_dependencies, '')
        ) AS intake_text
    FROM {CATALOG}.{SCHEMA}.project_intakes
),
planview AS (
    SELECT
        work_id                     AS project_id,
        project_name,
        line_of_businessprogram     AS line_of_business,
        work_type                   AS project_size,
        CONCAT_WS(' | ',
            COALESCE(project_name, ''),
            COALESCE(project_description, ''),
            COALESCE(known_risks_constraints_dependencies, ''),
            COALESCE(work_type, ''),
            COALESCE(line_of_businessprogram, '')
        ) AS planview_text
    FROM {CATALOG}.{SCHEMA}.planview_odata_project_dimension
),
combined AS (
    SELECT
        COALESCE(i.project_id, p.project_id)            AS project_id,
        COALESCE(i.project_name, p.project_name)        AS project_name,
        CASE
            WHEN i.project_id IS NOT NULL AND p.project_id IS NOT NULL THEN 'both'
            WHEN i.project_id IS NOT NULL THEN 'intake'
            ELSE 'planview'
        END                                             AS project_source,
        COALESCE(i.project_size, p.project_size)        AS project_size,
        COALESCE(i.line_of_business, p.line_of_business) AS line_of_business,
        CONCAT_WS(' ||| ',
            COALESCE(i.intake_text, ''),
            COALESCE(p.planview_text, '')
        )                                               AS base_text
    FROM intake i
    FULL OUTER JOIN planview p ON i.project_id = p.project_id
)
SELECT
    c.project_id,
    c.project_name,
    c.project_source,
    c.project_size,
    c.line_of_business,
    -- search_text: base + tags + transcript (truncated to ~8000 chars
    -- to stay within embedding model context window)
    LEFT(
        CONCAT_WS(' ||| ',
            c.base_text,
            COALESCE(w.all_tags, ''),
            COALESCE(w.all_titles, ''),
            COALESCE(t.transcript_text, '')
        ), 8000
    )                       AS search_text,
    t.transcript_text,
    w.all_tags              AS workitem_tags,
    w.workitem_count
FROM combined c
LEFT JOIN _workitem_tags   w ON c.project_id = w.project_id
LEFT JOIN _ram_transcripts t ON c.project_id = t.project_id
""")

count = spark.sql(f"SELECT COUNT(*) AS n FROM {CORPUS_TABLE}").collect()[0]["n"]
print(f"\nCorpus table created: {CORPUS_TABLE}  ({count} rows)")

# Show a sample
spark.sql(f"""
SELECT project_id, project_name, project_source,
       LENGTH(search_text) AS text_len,
       transcript_text IS NOT NULL AS has_transcript,
       workitem_count
FROM {CORPUS_TABLE}
ORDER BY project_id
LIMIT 10
""").show(truncate=False)
