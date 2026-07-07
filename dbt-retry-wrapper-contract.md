# dbt Retry Wrapper Contract

This document defines the contract for enabling dbt retry in Cloud Run without relying on local state.

## Goal

Allow operators to trigger `dbt retry` in runtime by restoring prior run artifacts from GCS, while keeping default behavior unchanged (`seed + build`).

## Non-Goals

- No change to CI scope in GitHub Actions.
- No warehouse-backed dbt execution in CI.
- No automatic retries on every failure unless explicitly enabled.

## Runtime Modes

The runtime wrapper should support two modes.

1. `build` (default)
2. `retry`

When `DBT_RUN_MODE` is absent, runtime must behave exactly as today.

## Environment Variable Contract

### Existing variables (unchanged)

- `DBT_FROM_DATE`
- `DBT_TO_DATE`
- `DBT_SELECT`
- `DBT_VARS_JSON`
- `DBT_LOG_BUCKET`

### New variables

- `DBT_RUN_MODE`
  - allowed: `build`, `retry`
  - default: `build`

- `DBT_RETRY_SOURCE`
  - allowed: `latest_failed`, `execution_id`
  - default: `latest_failed`

- `DBT_RETRY_EXECUTION_ID`
  - required only when `DBT_RETRY_SOURCE=execution_id`

- `DBT_RETRY_FALLBACK`
  - allowed: `build`, `fail`
  - default: `build`
  - behavior when retry artifacts are missing or incompatible

- `DBT_RETRY_REQUIRE_MATCH`
  - allowed: `strict`, `relaxed`
  - default: `strict`
  - `strict`: project + image/git metadata must match
  - `relaxed`: allow retry with warning when metadata is partially missing

- `DBT_RETRY_SKIP_SEED`
  - allowed: `true`, `false`
  - default: `true`
  - in retry mode, decide whether `dbt seed` runs before `dbt retry`

## Workflow Payload Contract

The infra workflow payload can optionally include a `dbt_retry` object.

```json
{
  "region": "us-central1",
  "job_name": "dbt-test-job-c-run",
  "dbt_select": "tag:core+",
  "dbt_vars": {
    "from_date": "2026-07-01",
    "to_date": "2026-07-06"
  },
  "dbt_retry": {
    "enabled": true,
    "source": "latest_failed",
    "execution_id": "",
    "fallback": "build",
    "require_match": "strict",
    "skip_seed": true
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

### Mapping rules

- if `dbt_retry.enabled=true`, workflow sets `DBT_RUN_MODE=retry`
- map `dbt_retry.source` to `DBT_RETRY_SOURCE`
- map `dbt_retry.execution_id` to `DBT_RETRY_EXECUTION_ID`
- map `dbt_retry.fallback` to `DBT_RETRY_FALLBACK`
- map `dbt_retry.require_match` to `DBT_RETRY_REQUIRE_MATCH`
- map `dbt_retry.skip_seed` to `DBT_RETRY_SKIP_SEED`

If `dbt_retry` is absent, runtime remains in `build` mode.

## GCS Artifact Layout

Use a stable folder layout under `DBT_LOG_BUCKET` for each execution.

```text
<date>/<hour>/<execution-id>-<timestamp>/
  logs/...
  target/run_results.json
  target/manifest.json
  target/perf_info.json
  target/partial_parse.msgpack
  metadata/runtime_metadata.json
```

Optional: include additional target files if needed by adapter behavior.

## Metadata Contract

Write `metadata/runtime_metadata.json` after each run.

```json
{
  "project_name": "dbt_airflow_test",
  "job_name": "dbt-test-job-c-run",
  "run_mode": "build",
  "dbt_command": "dbt build",
  "status": "error",
  "execution_id": "<cloud-run-execution>",
  "workflow_execution_id": "<workflow-execution>",
  "image_ref": "us-central1-docker.pkg.dev/...:sha",
  "git_sha": "<optional-sha>",
  "timestamp_utc": "2026-07-06T12:00:00Z"
}
```

This metadata is used to choose retry candidates and enforce compatibility.

## Retry Candidate Selection

### Latest failed mode

1. list objects in the bucket for this job prefix
2. read recent `runtime_metadata.json`
3. pick most recent artifact set with `status=error`
4. verify required files exist
5. apply compatibility checks

### Explicit execution mode

1. resolve the provided execution id
2. read metadata and required target artifacts
3. apply compatibility checks

## Compatibility Checks

In strict mode:

- project name must match current project
- job name must match current job
- if image ref or git sha exists in metadata, it must match current runtime when those fields are available

If strict check fails:

- if fallback is `build`, log warning and run `seed + build`
- if fallback is `fail`, exit non-zero

In relaxed mode:

- allow retry if required artifacts exist, log warning for mismatches

## Required Files For Retry

At minimum:

- `target/run_results.json`

Recommended:

- `target/manifest.json`
- `target/partial_parse.msgpack`
- `metadata/runtime_metadata.json`

If minimum files are missing:

- fallback behavior follows `DBT_RETRY_FALLBACK`

## Runtime Decision Table

1. `DBT_RUN_MODE=build`
- run `dbt seed`
- run `dbt build`

2. `DBT_RUN_MODE=retry` with valid artifacts
- optionally run `dbt seed` when `DBT_RETRY_SKIP_SEED=false`
- run `dbt retry`

3. `DBT_RUN_MODE=retry` with missing or incompatible artifacts
- `DBT_RETRY_FALLBACK=build`: run normal build path
- `DBT_RETRY_FALLBACK=fail`: stop with error

## Infra/Workflow Changes Needed

In workflow config:

- parse optional `dbt_retry` object
- map retry fields to env vars in Cloud Run `containerOverrides`
- keep defaults so existing payloads continue to work

In Terraform:

- only update workflow source if env mapping changes
- ensure runtime identity has object read/list permissions on `DBT_LOG_BUCKET`

## Runtime Script Changes Needed

In runtime wrapper:

1. add mode resolver
2. add retry artifact restore function
3. add compatibility check function
4. add retry execution path
5. persist metadata after success/failure
6. keep artifact upload behavior for both build and retry modes

## Logging Expectations

Log all key decisions:

- selected run mode
- retry source and candidate execution
- compatibility check outcome
- fallback action taken
- final dbt command and exit code

## Failure Handling

- always attempt artifact upload, even when retry/build fails
- include reason for failure in metadata
- return non-zero exit code when configured fallback is fail

## Security

- do not embed secrets in metadata or logs
- do not upload environment dumps
- keep secret values masked in command output

## Rollout Plan

1. Phase 1: add metadata writing and expanded artifact upload
2. Phase 2: add retry restore path behind `DBT_RUN_MODE=retry`
3. Phase 3: add workflow payload support for `dbt_retry`
4. Phase 4: document operator runbook and examples

## Backward Compatibility

- existing manual workflow payloads remain valid
- existing schedule runs remain valid
- default run mode stays `build`
- CI behavior remains unchanged

## Open Questions Before Implementation

1. Should strict mode require exact git sha match always, or only when sha is available?
2. Should retry run with previous selection automatically, or allow new selection overrides?
3. Do we want max retry artifact age, for example ignore runs older than 7 days?
4. Should retry metadata live in same bucket prefix or a dedicated index prefix?
