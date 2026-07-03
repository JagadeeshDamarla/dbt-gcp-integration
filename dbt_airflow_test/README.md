Welcome to your dbt Cloud Run project.

## Local run

Set required Snowflake and dbt variables:

```bash
export SNOWFLAKE_ACCOUNT="..."
export SNOWFLAKE_USER="..."
export SNOWFLAKE_PASSWORD="..."
export SNOWFLAKE_ROLE="..."
export SNOWFLAKE_DATABASE="..."
export SNOWFLAKE_WAREHOUSE="..."
export SNOWFLAKE_SCHEMA="..."
export DBT_THREADS="4"
```

Then run:

```bash
dbt run --profiles-dir . --vars '{"from_date":"2026-07-01", "to_date":"2026-07-01"}'
```

## Cloud Run runtime variables

The Cloud Run Job should inject these environment variables:

- `DBT_FROM_DATE`
- `DBT_TO_DATE`
- `DBT_LOG_BUCKET`
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_ROLE`
- `SNOWFLAKE_DATABASE`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_SCHEMA`
- `DBT_THREADS` (optional, default `4`)

## GitHub Actions variables

The deploy workflow expects these repository variables to be set (typically from your Terraform-managed environment):

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `ARTIFACT_IMAGE_NAME`
- `CLOUD_RUN_JOB_NAME`
- `WORKFLOW_NAME`
- `WIF_PROVIDER`
- `DEPLOYER_SERVICE_ACCOUNT`
