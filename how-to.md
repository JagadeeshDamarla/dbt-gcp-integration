# How To: Add Or Change A dbt Project

This guide covers two common tasks:
1. Add a brand new dbt project.
2. Modify an existing dbt project.

The setup is split across two repositories:
1. `dbt-gcp-integration`: dbt code, Docker image build, deploy workflow.
2. `dbt-gcp-infra`: Cloud Run Job, Workflow, Scheduler, IAM, Terraform.

## Architecture Summary

For each dbt project:
1. The integration repo builds and pushes a container image.
2. The deploy workflow updates the existing Cloud Run Job image.
3. The infra repo defines the Cloud Run Job, Workflow, and Scheduler.
4. The Workflow triggers the Cloud Run Job on schedule or manual execution.

## Prerequisites

Before adding a new project, make sure you have:
1. A dbt project folder with `dbt_project.yml`, `profiles.yml`, `requirements.txt`, `Dockerfile`, and runtime script.
2. A target GCP project, region, Artifact Registry repository, and Cloud Run naming convention.
3. A service account that the Cloud Run Job and Workflow can use.
4. Access to required secrets such as `SNOWFLAKE_PASSWORD` and `SLACK_WEBHOOK`.
5. Terraform backend settings for the infra repo.

## Add A New dbt Project

### Step 1: Create the dbt project in integration

In [dbt-gcp-integration](./):
1. Copy [dbt_airflow_test](./dbt_airflow_test) to a new folder, for example `my_new_project`.
2. Update the dbt SQL, seeds, tests, `dbt_project.yml`, `profiles.yml`, and `Dockerfile` as needed.
3. Make sure the runtime script still works for your project layout.

Minimum files expected in the new project folder:
1. `dbt_project.yml`
2. `profiles.yml`
3. `requirements.txt`
4. `Dockerfile`
5. runtime shell script

### Step 2: Register the project in deploy workflow mapping

Update [dbt_deploy.yml](./.github/workflows/dbt_deploy.yml) and [resolve_deploy_project.py](./scripts/resolve_deploy_project.py).

In the workflow:
1. Add your project to the `workflow_dispatch.inputs.project.options` list.
2. Add a matching entry in `PROJECT_SETTINGS` inside [resolve_deploy_project.py](./scripts/resolve_deploy_project.py).

Each `PROJECT_SETTINGS` entry must set:
1. `DBT_PROJECT_DIR`
2. `IMAGE_NAME`
3. `JOB_NAME`
4. `DBT_MODEL_SELECTOR` (optional but recommended for CI speed)

### Step 3: Add infrastructure in infra repo

In [dbt-gcp-infra/infra](../dbt-gcp-infra/infra):
1. Copy [dbt_airflow_test.tf](../dbt-gcp-infra/infra/dbt_airflow_test.tf) to a new file such as `my_new_project.tf`.
2. Update:
   - `job_name`
   - `container_image`
   - `workflow_name`
   - `runtime_service_account`
   - `log_bucket_name`
   - `workflow_schedule_cron`
   - `workflow_schedule_time_zone`
   - `snowflake_password_secret_id`
   - `slack_webhook_secret_id`
3. Keep the module pattern the same as the existing file.

This is the rock-style pattern now used in the infra repo: one pipeline, one `.tf` file.

### Step 4: Review shared Terraform settings

Check these shared infra files only if your new project needs shared changes:
1. [main.tf](../dbt-gcp-infra/infra/main.tf)
2. [variables.tf](../dbt-gcp-infra/infra/variables.tf)
3. [providers.tf](../dbt-gcp-infra/infra/providers.tf)
4. [prod.tfvars.example](../dbt-gcp-infra/infra/prod.tfvars.example)

In most cases, you should not need to change them for a normal new project.

### Step 5: Apply infrastructure

In `dbt-gcp-infra`:

```bash
cd infra
terraform init -backend-config="bucket=<terraform-state-bucket>" -backend-config="prefix=<terraform-state-prefix>"
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars
```

Or use the GitHub Actions Terraform workflow in [tf-pipeline.yml](../dbt-gcp-infra/.github/workflows/tf-pipeline.yml).

### Step 6: Deploy the dbt image

In `dbt-gcp-integration`, run the GitHub Actions workflow in [.github/workflows/dbt_deploy.yml](./.github/workflows/dbt_deploy.yml) and select the new `project`.

The deploy workflow will:
1. Resolve project settings via [resolve_deploy_project.py](./scripts/resolve_deploy_project.py).
2. Run `dbt seed` and `dbt build`.
3. Build and push the Docker image.
4. Update the target Cloud Run Job image.

### Step 7: Optional payload-driven runs for same project

You can run different model groups from the same Cloud Run Job and Workflow by passing payload parameters:
1. `dbt_select`: selector string, for example `model_a+`.
2. `dbt_vars`: JSON object, for example `{ "from_date": "2026-07-01", "to_date": "2026-07-01", "country": "DE" }`.

The Workflow converts `dbt_vars` to `DBT_VARS_JSON` and passes both to the runtime script.

### Step 8: Validate end to end

After infra apply and deploy:
1. Verify the Cloud Run Job exists.
2. Verify the Workflow exists.
3. Verify the Scheduler exists if this project is scheduled.
4. Trigger a manual Workflow run.
5. Confirm dbt execution logs and Slack notifications.

## Modify An Existing dbt Project

### Case 1: Change only dbt logic

If you are only changing SQL, tests, seeds, or macros in an existing project:
1. Update the files inside the existing project folder in `dbt-gcp-integration`.
2. Run the deploy workflow in [.github/workflows/dbt_deploy.yml](./.github/workflows/dbt_deploy.yml).
3. No Terraform change is needed.

Examples:
1. Add a new model.
2. Update SQL transformations.
3. Add schema tests or singular tests.
4. Update seed data.

### Case 2: Change deployment behavior

If you are changing what the deploy workflow should test or build:
1. Update the matching `project` entry in [.github/workflows/dbt_deploy.yml](./.github/workflows/dbt_deploy.yml).
2. Update the matching `PROJECT_SETTINGS` entry in [resolve_deploy_project.py](./scripts/resolve_deploy_project.py).

Examples:
1. Change `DBT_PROJECT_DIR`.
2. Change `DBT_MODEL_SELECTOR` used by CI.
3. Change Artifact Registry image name.
4. Change Cloud Run job name reference in integration.

### Case 3: Change infrastructure behavior

If you are changing schedule, workflow name, runtime service account, secrets, or log bucket:
1. Update the matching `.tf` file in `dbt-gcp-infra/infra`.
2. Run Terraform plan/apply.

Examples:
1. Change scheduler cron.
2. Pause or resume schedule.
3. Change secret IDs.
4. Change Cloud Run Job name.
5. Change Workflow name.

## Typical Change Matrix

Use this rule of thumb:
1. dbt SQL/test/container change only: integration repo only.
2. Cloud Run / Workflow / Scheduler / IAM change: infra repo only.
3. New project onboarding: both repos.
4. Job naming or deploy mapping change: usually both repos.

## Minimal New Project Checklist

Before you consider a new project complete, confirm all of the following:
1. New project folder exists in `dbt-gcp-integration`.
2. New `project` option exists in [.github/workflows/dbt_deploy.yml](./.github/workflows/dbt_deploy.yml).
3. New `PROJECT_SETTINGS` entry exists in [resolve_deploy_project.py](./scripts/resolve_deploy_project.py).
4. New pipeline `.tf` file exists in [dbt-gcp-infra/infra](../dbt-gcp-infra/infra).
5. Terraform apply completed successfully.
6. Deploy workflow completed successfully.
7. Manual Workflow execution succeeds.
8. Scheduled execution is visible if scheduling is enabled.

## Common Mistakes

1. Adding a new dbt folder in integration but forgetting to add the matching `project` option in [.github/workflows/dbt_deploy.yml](./.github/workflows/dbt_deploy.yml) and mapping in [resolve_deploy_project.py](./scripts/resolve_deploy_project.py).
2. Updating integration job names without matching the `.tf` file in `dbt-gcp-infra`.
3. Applying Terraform before checking secret access and service account permissions.
4. Changing schedule or workflow names only in integration; those belong to infra.
5. Forgetting that deploy updates the image, but actual dbt execution happens later through Workflow or Scheduler.

## Quick Reference

Integration repo files:
1. [.github/workflows/dbt_deploy.yml](./.github/workflows/dbt_deploy.yml)
2. [scripts/resolve_deploy_project.py](./scripts/resolve_deploy_project.py)
3. [dbt_airflow_test](./dbt_airflow_test)

Infra repo files:
1. [infra/dbt_airflow_test.tf](../dbt-gcp-infra/infra/dbt_airflow_test.tf)
2. [infra/main.tf](../dbt-gcp-infra/infra/main.tf)
3. [infra/variables.tf](../dbt-gcp-infra/infra/variables.tf)
4. [infra/README.md](../dbt-gcp-infra/infra/README.md)