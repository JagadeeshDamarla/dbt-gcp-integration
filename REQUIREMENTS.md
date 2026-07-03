# dbt-gcp-integration Requirements

## 1. Problem Statement
The repository must provide a reliable and repeatable way to package dbt code into a container image and deploy that image to an existing Cloud Run Job.

Primary business goals:
- Ship dbt model changes safely without recreating infrastructure resources.
- Keep application delivery fast and independent from infrastructure lifecycle.
- Ensure runtime behavior is deterministic when executed by GCP Workflows.

## 2. Scope and Ownership
This repository owns:
- dbt project code under dbt_airflow_test
- container build definition (Dockerfile + runtime script)
- image publish and Cloud Run Job image update workflow

This repository does not own:
- Cloud Run Job creation/deletion
- Workflows resource creation/deletion
- Cloud Scheduler resource lifecycle
- IAM policy lifecycle

Those are owned by dbt-gcp-infra.

## 3. Architecture Followed
Current architecture in this repo:
- GitHub Actions workflow performs manual build and deploy on demand.
- Built image is pushed to Artifact Registry.
- Existing Cloud Run Job image is updated to the new image digest/tag.
- Actual model execution is performed later by Workflow trigger (manual or scheduler), not by this deployment workflow.

Key implication:
- Deploy success does not mean dbt models ran.
- Deploy success only means the runnable image has been updated.

## 4. Solution Approach Followed
### 4.1 Build and Deploy
Workflow file:
- .github/workflows/dbt_deploy.yml

Workflow behavior:
1. Authenticate using Workload Identity Federation.
2. Login to Artifact Registry.
3. Build and push image from dbt_airflow_test context.
4. Validate target Cloud Run Job exists.
5. Update Cloud Run Job image.

### 4.2 Runtime Execution
Runtime script:
- dbt_airflow_test/run_dbt_with_log_upload.sh

Runtime behavior:
1. Expects DBT_FROM_DATE and DBT_TO_DATE from Workflow overrides.
2. Runs dbt build with those vars.
3. Uploads logs/artifacts to GCS bucket when available.
4. Returns dbt process exit code.

### 4.3 Connection Configuration
Profile file:
- dbt_airflow_test/profiles.yml

Current policy:
- Non-secret Snowflake fields are static in profile.
- Only SNOWFLAKE_PASSWORD is injected at runtime from Secret Manager via Cloud Run Job env secret ref.

## 5. Functional Requirements
- FR-1: Manual deployment workflow must build and publish image successfully.
- FR-2: Deployment workflow must update only existing Cloud Run Job image.
- FR-3: No infrastructure resource creation should happen in this repo workflow.
- FR-4: Runtime must require date window vars for deterministic processing.
- FR-5: dbt runtime must return non-zero on model failure.
- FR-6: Artifact/log upload should not mask dbt execution exit code.

## 6. Non-Functional Requirements
- NFR-1: Deployment should complete without interactive prompts.
- NFR-2: Authentication must use OIDC/WIF; no long-lived JSON keys.
- NFR-3: Build should be reproducible from current repo state.
- NFR-4: Runtime contract must remain stable for infra-triggered workflow executions.

## 7. Ad-hoc Run Requirements
Ad-hoc runs are executed through GCP Workflows (preferred) so notification and orchestration behavior is preserved.

Required payload fields:
- notification_template

Recommended payload fields:
- region
- job_name
- dbt_params.from_date
- dbt_params.to_date

Example command:
```bash
gcloud workflows executions run dbt_test_workflow_new \
  --project=new-map-project-1538399427267 \
  --location=us-central1 \
  --data='{"region":"us-central1","job_name":"dbt-test-job-c-run","dbt_params":{"from_date":"2026-07-02","to_date":"2026-07-02"},"notification_template":{"provider":"slack","slack_webhook_secret_resource":"projects/995265336172/secrets/SLACK_WEBHOOK","attributes":{"region":"region","operation":"operation","workflow_execution":"workflow_execution"},"status_icons":{"started":":information_source:","success":":white_check_mark:","failure":":x:"}}}'
```

## 8. Cancellation Requirements
### 8.1 Cancel Workflow Execution
List executions:
```bash
gcloud workflows executions list dbt_test_workflow_new \
  --project=new-map-project-1538399427267 \
  --location=us-central1
```

Cancel an execution:
```bash
gcloud workflows executions cancel EXECUTION_ID \
  --workflow=dbt_test_workflow_new \
  --project=new-map-project-1538399427267 \
  --location=us-central1
```

### 8.2 Cancel Running Cloud Run Job Execution
List job executions:
```bash
gcloud run jobs executions list \
  --job=dbt-test-job-c-run \
  --project=new-map-project-1538399427267 \
  --region=us-central1
```

Cancel execution:
```bash
gcloud run jobs executions cancel EXECUTION_NAME \
  --project=new-map-project-1538399427267 \
  --region=us-central1
```

## 9. Notifications and Observability
Notification path:
- Slack notifications are sent by Workflow steps (start/success/failure).
- Slack webhook URL is read from Secret Manager resource provided in notification_template.

Where to check failures:
1. GCP Workflows execution details
2. Cloud Run Job execution logs
3. GCS uploaded dbt artifacts (logs, run_results.json, manifest.json)
4. GitHub Actions logs for deploy stage

## 10. Common Failure Modes
- Missing DBT_FROM_DATE/DBT_TO_DATE in runtime execution.
- SNOWFLAKE_PASSWORD secret not accessible by runtime service account.
- Cloud Run Job image not updated due to Artifact Registry auth/permission.
- Workflow input missing notification_template.

## 11. Acceptance Criteria
- AC-1: Deploy workflow updates image without creating infra resources.
- AC-2: Manual Workflow execution with valid payload runs dbt models end to end.
- AC-3: Failed dbt run results in failed Workflow execution.
- AC-4: Slack start and terminal status notifications are visible.
- AC-5: Job cancellation commands terminate active runs as expected.
