# AGENTS.md

This file helps AI coding agents work safely and consistently in this repository.

## Repository Purpose

This repository owns:

- dbt project code
- container image build and push
- deploy workflow that performs static validation and updates Cloud Run Job image

Infrastructure resources are owned by the infra repository.

## Operating Rules

- Keep CI lightweight: CI should run static checks only (`dbt deps`, `dbt parse`).
- Keep execution in runtime: `dbt seed` and `dbt build` must run in Cloud Run runtime path.
- Do not introduce secrets into code. Use GCP Secret Manager patterns already in place.
- Use the smallest possible diff. Avoid unrelated edits.

## Read These Files First

1. `readmefirst.md`
2. `.github/workflows/dbt_deploy.yml`
3. `dbt_airflow_test/run_dbt_with_log_upload.sh`
4. `dbt_airflow_test/dbt_project.yml`
5. `dbt_airflow_test/profiles.yml`
6. `dbt_airflow_test/models/example/schema.yml`
7. `../dbt-gcp-infra/infra/config/workflow.yaml`
8. `../dbt-gcp-infra/infra/dbt_airflow_test.tf`

## Change Ownership

- Integration repo changes:
  - models, snapshots, seeds, tests, macros
  - runtime shell script
  - deploy workflow mapping
- Infra repo changes:
  - Cloud Run Job
  - Workflow and Scheduler
  - IAM and Secret Manager access
  - Terraform files

If both image behavior and runtime contract change, update both repos together.

## PR Approval Checklist

- [ ] Change belongs to the correct repo.
- [ ] CI remains static-check only.
- [ ] Runtime execution remains in Cloud Run.
- [ ] Folder placement is correct (`models`, `snapshots`, `seeds`, `macros`, `tests`).
- [ ] Generic tests use current syntax (`arguments:` where needed).
- [ ] `ref()` dependencies are correct.
- [ ] Runtime selector/tag path remains consistent.
- [ ] Runtime artifact upload behavior is preserved.
- [ ] Cross-repo updates are made when needed.
- [ ] Secrets are not hardcoded.
- [ ] Validation evidence is included.
- [ ] Docs are updated when behavior changes.

## Agent Task Handoff Template

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
