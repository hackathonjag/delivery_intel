-- Databricks notebook source
-- DBTITLE 1,Delivery Intelligence Data Ingestion
-- MAGIC %md
-- MAGIC # Delivery Intelligence Data Ingestion
-- MAGIC
-- MAGIC Reads all CSV files from `/Volumes/dpm_dev/mlops/test/delivery/generated_delivery_intelligence_data/` using `read_files` and creates external Delta tables in `dpm_dev.mlops` at `abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/`.

-- COMMAND ----------

SELECT * FROM read_files(
  '/Volumes/dpm_dev/mlops/test/delivery/generated_delivery_intelligence_data/devops_workitem_relations.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest devops_workitem_relations
CREATE OR REPLACE TABLE dpm_dev.mlops.devops_workitem_relations
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/devops_workitem_relations'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/devops_workitem_relations.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest devops_workitemrevisions_analytics
CREATE OR REPLACE TABLE dpm_dev.mlops.devops_workitemrevisions_analytics
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/devops_workitemrevisions_analytics'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/devops_workitemrevisions_analytics.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest devops_workitems_details
CREATE OR REPLACE TABLE dpm_dev.mlops.devops_workitems_details
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/devops_workitems_details'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/devops_workitems_details.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest oracle_hcm_teams
CREATE OR REPLACE TABLE dpm_dev.mlops.oracle_hcm_teams
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/oracle_hcm_teams'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/oracle_hcm_teams.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest oracle_hcm_worker_skills
CREATE OR REPLACE TABLE dpm_dev.mlops.oracle_hcm_worker_skills
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/oracle_hcm_worker_skills'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/oracle_hcm_worker_skills.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest oracle_hcm_workers
CREATE OR REPLACE TABLE dpm_dev.mlops.oracle_hcm_workers
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/oracle_hcm_workers'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/oracle_hcm_workers.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest planview_odata_project_dimension
CREATE OR REPLACE TABLE dpm_dev.mlops.planview_odata_project_dimension
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/planview_odata_project_dimension'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/planview_odata_project_dimension.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest project_approval_dependencies
CREATE OR REPLACE TABLE dpm_dev.mlops.project_approval_dependencies
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/project_approval_dependencies'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/project_approval_dependencies.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest project_estimate_summary
CREATE OR REPLACE TABLE dpm_dev.mlops.project_estimate_summary
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/project_estimate_summary'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/project_estimate_summary.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest project_intakes
CREATE OR REPLACE TABLE dpm_dev.mlops.project_intakes
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/project_intakes'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/project_intakes.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest project_resource_assignments
CREATE OR REPLACE TABLE dpm_dev.mlops.project_resource_assignments
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/project_resource_assignments'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/project_resource_assignments.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest project_role_estimates
CREATE OR REPLACE TABLE dpm_dev.mlops.project_role_estimates
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/project_role_estimates'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/project_role_estimates.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest project_task_dependencies
CREATE OR REPLACE TABLE dpm_dev.mlops.project_task_dependencies
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/project_task_dependencies'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/project_task_dependencies.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest resource_availability
CREATE OR REPLACE TABLE dpm_dev.mlops.resource_availability
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/resource_availability'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/resource_availability.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest resource_pool
CREATE OR REPLACE TABLE dpm_dev.mlops.resource_pool
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/resource_pool'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/resource_pool.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest similar_project_matches
CREATE OR REPLACE TABLE dpm_dev.mlops.similar_project_matches
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/similar_project_matches'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/similar_project_matches.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest snow_change_request
CREATE OR REPLACE TABLE dpm_dev.mlops.snow_change_request
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/snow_change_request'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/snow_change_request.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest snow_cmdb_ci_service
CREATE OR REPLACE TABLE dpm_dev.mlops.snow_cmdb_ci_service
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/snow_cmdb_ci_service'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/snow_cmdb_ci_service.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest snow_incidents
CREATE OR REPLACE TABLE dpm_dev.mlops.snow_incidents
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/snow_incidents'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/snow_incidents.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest ukg_wfm_schedules
CREATE OR REPLACE TABLE dpm_dev.mlops.ukg_wfm_schedules
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/ukg_wfm_schedules'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/ukg_wfm_schedules.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest ukg_wfm_timecards
CREATE OR REPLACE TABLE dpm_dev.mlops.ukg_wfm_timecards
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/ukg_wfm_timecards'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/ukg_wfm_timecards.csv',
  format => 'csv',
  header => true
)

-- COMMAND ----------

-- DBTITLE 1,Ingest workforce_capacity_weekly
CREATE OR REPLACE TABLE dpm_dev.mlops.workforce_capacity_weekly
LOCATION 'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/workforce_capacity_weekly'
AS SELECT * FROM read_files(
  'abfss://mlops@gmfcusdevdpmconsumesa.dfs.core.windows.net/volume/test/delivery/generated_delivery_intelligence_data/workforce_capacity_weekly.csv',
  format => 'csv',
  header => true
)