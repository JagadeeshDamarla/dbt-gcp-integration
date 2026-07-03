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
- `SNOWFLAKE_PASSWORD`

The dbt profile currently uses hardcoded non-secret Snowflake config values and reads only `SNOWFLAKE_PASSWORD` from runtime.

## Manual Workflow Run Template

Use this payload when manually executing the GCP Workflow:

```json
{
	"region": "us-central1",
	"job_name": "dbt-test-job-c-run",
	"dbt_params": {
		"from_date": "2026-07-02",
		"to_date": "2026-07-02"
	},
	"notification_template": {
		"provider": "slack",
		"slack_webhook_secret_resource": "projects/995265336172/secrets/SLACK_WEBHOOK",
		"attributes": {
			"region": "region",
			"operation": "operation",
			"workflow_execution": "workflow_execution"
		},
		"status_icons": {
			"started": ":information_source:",
			"success": ":white_check_mark:",
			"failure": ":x:"
		}
	}
}
```

Execute via `gcloud`:

```bash
gcloud workflows executions run dbt_test_workflow_new \
	--project=new-map-project-1538399427267 \
	--location=us-central1 \
	--data='{"region":"us-central1","job_name":"dbt-test-job-c-run","dbt_params":{"from_date":"2026-07-02","to_date":"2026-07-02"},"notification_template":{"provider":"slack","slack_webhook_secret_resource":"projects/995265336172/secrets/SLACK_WEBHOOK","attributes":{"region":"region","operation":"operation","workflow_execution":"workflow_execution"},"status_icons":{"started":":information_source:","success":":white_check_mark:","failure":":x:"}}}'
```

Notes:
- `dbt_params` is optional; if omitted, Workflow defaults are used.
- Keep `notification_template` in the payload because the current Workflow expects it.

## GitHub Actions variables

The deploy workflow expects these repository variables to be set (typically from your Terraform-managed environment):

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `ARTIFACT_IMAGE_NAME`
- `CLOUD_RUN_JOB_NAME`
- `WORKFLOW_NAME`
- `WIF_PROVIDER`
- `DEPLOYER_SERVICE_ACCOUNT`

The deploy workflow also requires this repository secret because dbt tests are executed before image deployment:

- `SNOWFLAKE_PASSWORD`
