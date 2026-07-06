# Read Me First

This repository is the dbt application side of the platform. It owns the dbt project code, the container image build, and the GitHub Actions deploy workflow. The matching infra repo owns the Cloud Run Job, Workflow, Scheduler, IAM, and secret references.

## Current Setup

The current flow is intentionally split into two phases:

1. GitHub Actions deploy phase in this repo.
2. Runtime execution phase in GCP.

What the deploy phase does now:

- resolves the selected project mapping from `.github/workflows/dbt_deploy.yml` through `scripts/resolve_deploy_project.py`
- validates the Artifact Registry repository and Cloud Run Job name
- installs Python/dbt dependencies from the project `requirements.txt`
- runs lightweight dbt validation only: `dbt deps` and `dbt parse`
- builds and pushes the container image
- updates the existing Cloud Run Job image

What the deploy phase does not do anymore:

- it does not run `dbt seed`
- it does not run `dbt build`
- it does not execute warehouse-backed dbt logic in CI

What the runtime phase does:

- the GCP Workflow triggers the Cloud Run Job
- the Workflow passes runtime parameters like `DBT_FROM_DATE`, `DBT_TO_DATE`, `DBT_SELECT`, and `DBT_VARS_JSON`
- the container entrypoint `run_dbt_with_log_upload.sh` resolves runtime vars
- the runtime script runs `dbt seed` first and then `dbt build`
- runtime artifacts and logs are uploaded to GCS for traceability

Important operating note:

- if you are deploying this in GCP, run the infra setup first
- the Cloud Run Job, Workflow, Scheduler, and IAM wiring must already exist before the deploy workflow can only update the image

Important rule examples:

- GCP infra change only: change the Cloud Run Job name, Workflow schedule, secret ids, runtime service account, or IAM bindings in the infra repo
- dbt code change only: add or edit a model SQL file, snapshot, macro, seed, or test in this repo without touching Terraform
- shared change: if you rename a job or add a new project, update both the integration deploy mapping and the infra Terraform file together

## Prerequisites

Before you work on this repo, make sure you have:

- access to the target GCP project
- `gcloud` authenticated to the right account and project
- access to Secret Manager for Snowflake and Slack secrets
- Docker installed if you want to build the image locally
- Python 3.10 or compatible local tooling if you want to run dbt outside the container
- access to the infra repo so you can update the Workflow or Cloud Run wiring when needed

Required secrets and runtime dependencies:

- `SNOWFLAKE_PASSWORD` comes from GCP Secret Manager at runtime
- `SLACK_WEBHOOK` is used by the Workflow for notifications
- the project profile assumes Snowflake credentials are available through environment variables, not committed in the repo

## Repository File Map

### dbt project files

- `dbt_airflow_test/dbt_project.yml` defines project name, model paths, snapshot paths, seed paths, macro paths, and hooks
- `dbt_airflow_test/profiles.yml` defines the Snowflake target and reads `SNOWFLAKE_PASSWORD` from the environment
- `dbt_airflow_test/requirements.txt` pins dbt and helper Python dependencies
- `dbt_airflow_test/Dockerfile` builds the runtime image for Cloud Run
- `dbt_airflow_test/run_dbt_with_log_upload.sh` is the runtime entrypoint script

### dbt content folders

- `dbt_airflow_test/models/` contains views, tables, incremental models, and model-level schema tests
- `dbt_airflow_test/snapshots/` contains SCD2 snapshot definitions
- `dbt_airflow_test/seeds/` contains CSV seed data
- `dbt_airflow_test/macros/` contains reusable dbt macros
- `dbt_airflow_test/tests/` contains singular SQL tests
- `dbt_airflow_test/analyses/` contains ad hoc analysis SQL
- `dbt_airflow_test/target/` contains generated artifacts such as `manifest.json`, `run_results.json`, and compiled SQL

### deploy and orchestration files

- `.github/workflows/dbt_deploy.yml` performs the deploy-time validation, image build, and Cloud Run Job image update
- `scripts/resolve_deploy_project.py` maps the GitHub Actions `project` input to the right job name, image name, and dbt folder
- `../dbt-gcp-infra/infra/config/workflow.yaml` passes runtime vars and selectors into Cloud Run
- `../dbt-gcp-infra/infra/dbt_airflow_test.tf` defines the Cloud Run Job and Workflow wiring for this project

## What The Dockerfile Does

The Dockerfile is the runtime packaging step for the dbt job.

It does the following:

1. starts from `python:3.10-slim`
2. installs the small set of OS tools the container needs, such as `bash` and `git`
3. copies `requirements.txt` into the image and installs Python dependencies
4. copies the project files into `/usr/app/dbt`
5. makes `run_dbt_with_log_upload.sh` executable
6. sets `DBT_PROFILES_DIR=/usr/app/dbt`
7. starts the runtime wrapper as the container command

Why this matters:

- the image is self-contained
- the Cloud Run Job does not need to rebuild dbt dependencies at runtime
- runtime code stays consistent between local testing and deployed execution

## What profiles.yml Does

`profiles.yml` tells dbt how to connect to Snowflake.

In this repo:

- the target name is `dbt_airflow_test`
- the output type is Snowflake
- `SNOWFLAKE_PASSWORD` is injected at runtime through the environment
- account, user, role, database, warehouse, schema, and threads are configured there

Key point:

- do not hardcode secrets in `profiles.yml`
- keep only the secret reference in the file
- the actual password should come from Secret Manager or local environment variables

## How To Add Or Change Models

### Add a normal model

Put SQL models under `dbt_airflow_test/models/`.

Typical patterns:

- `models/staging/` for raw-to-clean views
- `models/intermediate/` for reusable transformations
- `models/marts/` for final tables or incrementals
- `models/example/` for small sample objects and onboarding work

Example:

```sql
-- models/marts/customer_summary.sql
{{ config(materialized='table', tags=['marts']) }}

select
    customer_id,
    count(*) as order_count
from {{ ref('orders') }}
group by 1
```

Common model materializations:

- `view` for lightweight transformation layers
- `table` for persisted outputs
- `incremental` for large fact-like datasets

### Add a snapshot

Put snapshots under `dbt_airflow_test/snapshots/`.

Snapshots are the right choice for slowly changing dimensions and historical tracking.

Example:

```sql
{% snapshot customer_scd2 %}
{{
  config(
    target_schema='snapshots',
    unique_key='customer_id',
    strategy='check',
    check_cols=['first_name', 'last_name', 'city', 'state', 'account_tier']
  )
}}

select *
from {{ ref('customer_seed_view') }}

{% endsnapshot %}
```

How snapshots fit into execution:

- `dbt build` can execute snapshots when they are selected or included in the graph
- downstream models should `ref()` the snapshot relation if they need the historical SCD2 output
- if a snapshot is part of the DAG, keep its selector consistent with the rest of the chain

### Add seed data

Put CSV files under `dbt_airflow_test/seeds/`.

Use seeds for:

- small static lookup tables
- local reference datasets
- lightweight test data

Important note:

- seeds are useful for small reference data, but they are usually not a good production pattern for large or frequently changing business data
- if the dataset is operational or high-volume, prefer a warehouse table, staged source, or another managed upstream input instead of a seed

### Add macros

Put reusable SQL logic under `dbt_airflow_test/macros/`.

Use macros for:

- repeated expressions
- date math helpers
- custom filter logic
- project-specific SQL generation

### Add singular tests

Put singular tests under `dbt_airflow_test/tests/`.

Singular tests are SQL files that return rows when something is wrong.

Example:

```sql
-- tests/customer_seed_view_no_future_signups.sql
select customer_id, signup_date
from {{ ref('customer_seed_view') }}
where signup_date > current_date
```

This test fails if any signup date is in the future.

### Add generic tests

Generic tests live in the model `schema.yml` files.

Current repo example style:

```yaml
columns:
  - name: customer_id
    tests:
      - not_null
      - unique
      - relationships:
          arguments:
            to: ref('customer_seed')
            field: customer_id
```

Another example:

```yaml
- name: account_tier
  tests:
    - not_null
    - accepted_values:
        arguments:
          values: ['gold', 'silver', 'bronze']
```

Use generic tests for:

- not null checks
- uniqueness checks
- accepted values checks
- relationships checks
- other common validations that should stay close to the model definition

## If You Want To Run By Tags

Tags are the cleanest way to run a subset of the project without editing SQL selection every time.

### Add tags in code

Example model config:

```sql
{{ config(materialized='view', tags=['core', 'staging']) }}
```

Example snapshot config:

```sql
{{
  config(
    unique_key='customer_id',
    strategy='check',
    check_cols=['first_name', 'last_name'],
    tags=['scd2']
  )
}}
```

### Change the selector used by the workflow

The runtime selector comes from the workflow payload field `dbt_select`.

That value is mapped in `../dbt-gcp-infra/infra/config/workflow.yaml` into the container environment variable `DBT_SELECT`.

If you want to change the default behavior for all runs, update the selector handling in `../dbt-gcp-infra/infra/config/workflow.yaml`.

If you only want to change a single execution, pass a different `dbt_select` value in the manual workflow payload.

Common selector examples:

- `tag:core`
- `tag:scd2`
- `tag:marts`
- `tag:core+` to include downstream children
- `+tag:marts` to include upstream parents

## Manual Workflow Trigger Example

The GCP Workflow expects a payload with the job name, region, notification template, and optional dbt runtime overrides.

Example payload:

```json
{
  "region": "us-central1",
  "job_name": "dbt-test-job-c-run",
  "dbt_select": "tag:core+",
  "dbt_params": {
    "from_date": "2026-07-01",
    "to_date": "2026-07-06"
  },
  "dbt_vars": {
    "from_date": "2026-07-01",
    "to_date": "2026-07-06",
    "country": "DE"
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

Example command:

```bash
gcloud workflows executions run dbt_test_workflow_new \
  --project=new-map-project-1538399427267 \
  --location=us-central1 \
  --data='{"region":"us-central1","job_name":"dbt-test-job-c-run","dbt_select":"tag:core+","dbt_params":{"from_date":"2026-07-01","to_date":"2026-07-06"},"dbt_vars":{"from_date":"2026-07-01","to_date":"2026-07-06","country":"DE"},"notification_template":{"provider":"slack","slack_webhook_secret_resource":"projects/995265336172/secrets/SLACK_WEBHOOK","attributes":{"region":"region","operation":"operation","workflow_execution":"workflow_execution"},"status_icons":{"started":":information_source:","success":":white_check_mark:","failure":":x:"}}}'
```

Notes:

- `dbt_params` is the date override path used by the Workflow
- `dbt_vars` takes precedence when present and is converted to JSON for the runtime container
- `notification_template` is still required by the current Workflow implementation

## How To Use dbt Retry

`dbt retry` reruns the last invocation from the first failed node instead of starting over from the beginning.

That makes it useful when:

- a run failed halfway through
- you want to resume after fixing a model or test failure
- you already have the previous `run_results.json` artifact available

Important limitations in this setup:

- the Cloud Run container is ephemeral
- `dbt retry` needs the previous run artifacts in `target/`
- this repo uploads `run_results.json` and logs to GCS after each run, but the runtime wrapper does not automatically restore them for retry

Practical workflow:

1. download or copy the previous `target/run_results.json` back into the working directory
2. make sure the previous `target/` artifacts are present if you need a full retry context
3. run `dbt retry` in the same project and profile context

Example local command:

```bash
dbt retry --project-dir dbt_airflow_test --profiles-dir dbt_airflow_test
```

If the previous command failed before any nodes actually executed, retry will have nothing useful to resume.

If the last command already succeeded, retry will usually be a no-op.

If you want a fully automated retry flow in Cloud Run, that would require a small wrapper change to restore the last artifact set before calling `dbt retry`.

## If You Want To Add A New Project, Not Just A New Model

A new project means a new dbt application folder and usually a new Cloud Run Job and Workflow too.

### In this repo

1. copy `dbt_airflow_test/` to a new folder
2. update the new folder’s `dbt_project.yml`, `profiles.yml`, `requirements.txt`, `Dockerfile`, and runtime script as needed
3. add a new `project` option to `.github/workflows/dbt_deploy.yml`
4. add a matching entry in `scripts/resolve_deploy_project.py`

### In the infra repo

1. add a new `*.tf` file under `../dbt-gcp-infra/infra/`
2. define the job name, workflow name, image name, schedule, secret ids, and runtime service account
3. apply Terraform after the backend and permissions are ready

### Operational sequence

1. update infra first if the new project needs a new job or workflow
2. then update the deploy workflow mapping in this repo
3. then deploy the image
4. finally test the runtime workflow execution

## Testing And Observability

### Why logs are uploaded to GCS

Cloud Run logs exist in the runtime environment and are useful, but they are not the best artifact for later debugging and comparison.

This project uploads the dbt runtime artifacts to GCS so you can:

- inspect failed runs after the job has exited
- review `run_results.json` and `manifest.json`
- compare logs across executions
- debug behavior without keeping a shell session alive

The runtime script uploads:

- `logs/`
- `target/run_results.json`
- `target/manifest.json`
- `target/perf_info.json`

### Local and CI checks

Use this repo’s lighter checks during deploy:

- `dbt deps`
- `dbt parse`

Use runtime or local execution for actual dbt execution:

- `dbt seed`
- `dbt build`
- `dbt test`
- `dbt snapshot`
- `dbt retry` when artifacts exist

### Test examples

Generic test example in `schema.yml`:

```yaml
- name: customer_id
  tests:
    - not_null
    - unique
```

Singular test example in `tests/`:

```sql
select customer_id
from {{ ref('customer_seed_view') }}
group by 1
having count(*) > 1
```

That singular test fails if duplicate customer ids appear.

## Best Practices

- keep secrets in GCP Secret Manager only
- use `ref()` instead of hardcoded relation names
- keep the deploy workflow lightweight and syntax-focused
- keep runtime execution in the container and workflow path
- use tags to control runtime scope instead of editing SQL selection on every run
- put SCD2 logic in snapshots, not in ad hoc table models
- use singular tests for business rules and generic tests for standard constraints
- store only source code in the repo, not generated `target/` artifacts
- update both repos when a change affects both the image and the runtime infrastructure

## Developer Onboarding Checklist

1. authenticate to GCP
2. confirm you can access the required secrets
3. understand whether your change belongs in the integration repo or infra repo
4. if you changed infrastructure, run the infra workflow or Terraform plan first
5. if you changed only dbt code, run the deploy workflow or local dbt validation
6. if you changed runtime selection, verify the workflow payload and selector
7. if you added a new project, update both the deploy workflow and infra tf file
8. review the architecture drift note if you want the current setup compared with the rock-style repo

## PR Approval Checklist

Use this checklist before approving a PR:

- [ ] the change is in the correct repository
- [ ] the change only touches the expected files
- [ ] CI still performs lightweight validation only (`dbt deps`, `dbt parse`)
- [ ] runtime dbt execution still happens in Cloud Run, not in GitHub Actions
- [ ] new dbt logic is in the correct folders (`models`, `snapshots`, `seeds`, `macros`, `tests`)
- [ ] generic test syntax uses `arguments:` where required
- [ ] new models and snapshots use `ref()` correctly
- [ ] selector/tag behavior is reflected in workflow payload handling
- [ ] runtime script behavior is preserved, including artifact upload to GCS
- [ ] infra-impacting changes are also updated in the infra repo
- [ ] new project onboarding updates both deploy mapping and infra Terraform
- [ ] secrets are still sourced from GCP Secret Manager and not committed in code
- [ ] validation evidence is included when relevant (`dbt parse`, `terraform validate`, workflow run evidence)
- [ ] docs are updated when user-facing behavior changes

## AI Agent Handoff Guide

If you need to hand this repo to an AI agent, provide these files first:

1. `readmefirst.md`
2. `.github/workflows/dbt_deploy.yml`
3. `dbt_airflow_test/run_dbt_with_log_upload.sh`
4. `dbt_airflow_test/dbt_project.yml`
5. `dbt_airflow_test/profiles.yml`
6. `dbt_airflow_test/models/example/schema.yml`
7. `../dbt-gcp-infra/infra/README.md`
8. `../dbt-gcp-infra/infra/config/workflow.yaml`
9. `../dbt-gcp-infra/infra/dbt_airflow_test.tf`

Brief template for the agent:

```text
Goal:

Repo:

Files to inspect first:

Files likely to change:

Constraints:
- keep CI limited to syntax/static checks
- keep dbt execution in runtime
- do not introduce new secret handling patterns
- do not change unrelated files

Success criteria:

Validation:
```

Quick ownership rule:

- integration repo: dbt SQL, snapshots, seeds, macros, tests, runtime script, deploy mapping
- infra repo: Cloud Run Job, Workflow, Scheduler, IAM, Secret Manager access, Terraform
- if image behavior and runtime infra contract both change, update both repos in the same change

## What To Read Next

- `../dbt-gcp-infra/infra/README.md` for the infrastructure side
- `ARCHITECTURE_DRIFT_ROCK_VS_CURRENT.md` for the current setup versus the rock-style reference
- `.github/workflows/dbt_deploy.yml` for the deploy-time checks and image update flow
- `scripts/resolve_deploy_project.py` for project mapping
- `dbt_airflow_test/run_dbt_with_log_upload.sh` for runtime dbt execution and log upload behavior
