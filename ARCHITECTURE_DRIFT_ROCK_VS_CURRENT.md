# Architecture Drift Summary: current setup vs rock_logistics

## Scope Compared

- Current setup:
  - `dbt-gcp-integration` for dbt code, image build, and deploy-time validation
  - `dbt-gcp-infra` for Terraform-managed Cloud Run, Workflow, Scheduler, IAM, and secret references
- Reference setup:
  - `rock_logistics_inbound-main`, which is a single monorepo with many pipeline folders, local run scripts, and layered Terraform stacks

## High-Level Architecture Snapshot

### Current setup

- Two-repo split with explicit ownership boundaries
- GitHub Actions in the integration repo now performs lightweight validation only:
  - resolves the selected project mapping
  - runs `dbt deps`
  - runs `dbt parse`
  - builds and pushes the image
  - updates the existing Cloud Run Job image
- Runtime dbt execution happens in Cloud Run through the Workflow and runtime shell script
- Workflow payloads can pass selectors and vars through `dbt_select` and `dbt_vars`
- Infra repo uses a rock-style one-pipeline-per-`tf` file pattern under `infra/`

### rock_logistics setup

- Single monorepo contains app code, multiple dbt projects, local scripts, CI workflows, and Terraform stacks
- Terraform is split across stage folders and shared modules
- Pipeline deploys and infra management are more tightly coupled inside one repository
- Runtime conventions are standardized across many jobs

## Drift Identified

1. Repo boundary and ownership model

- Current: clean split across two repos
- rock_logistics: one monorepo with app and infra co-located

2. Execution timing

- Current: GitHub Actions does not execute warehouse-backed dbt commands anymore
- Runtime dbt commands live in Cloud Run and are triggered by the Workflow
- rock_logistics: broader platform repo patterns with more build-orchestration coupling

3. Deployment coupling

- Current: app deploy updates image only; infra deploy owns resource lifecycle
- rock_logistics: build and infra deploy are orchestrated together in the same repo

4. Terraform topology

- Current: infra root is flattened and uses one pipeline file per dbt pipeline
- rock_logistics: layered stage folders with a larger shared platform surface

5. Runtime selector model

- Current: runtime can accept `dbt_select` and `dbt_vars` directly from the Workflow payload
- rock_logistics: more of the selection logic is embedded in repo-specific pipeline conventions and scripts

6. IAM and bootstrap handling

- Current: CI permissions are intentionally constrained, with a separate toggle for IAM ownership
- rock_logistics: assumes a stronger pre-provisioned platform baseline

7. Scale model

- Current: smaller footprint with one main dbt project and explicit mapping files
- rock_logistics: many pipelines and broader module reuse across the same monorepo

## What The Current Setup Is Doing Well

- clear separation of infra and app concerns
- runtime execution is now the source of truth for dbt runs
- deploy-time checks are lightweight and safer
- workflow payloads make tag-based and parameterized runs possible without changing SQL for every execution
- logs and artifacts are persisted to GCS for later analysis

## Remaining Drift From The Rock-Style Reference

1. The repos are still split instead of being one monorepo.
2. The contract between repos is still maintained manually through project mapping and Terraform naming.
3. The current setup is smaller and more explicit, so it lacks the broad multi-pipeline scaffolding of the reference repo.
4. The deployment path is simpler, but not yet fully automated across both repos.

## Suggested Target State

- keep the two-repo ownership model
- keep the rock-style one-`tf`-file-per-pipeline pattern in infra
- keep deploy-time dbt validation lightweight
- keep runtime execution in Cloud Run and let the Workflow own parameters, selectors, and notifications
- use a small shared contract for names, job ids, workflow ids, regions, and secret ids

## Practical Checklist For Future Changes

1. If the change is SQL-only, update the integration repo only.
2. If the change affects Cloud Run, Workflow, Scheduler, IAM, or secrets, update the infra repo.
3. If the change affects both the image and the runtime wiring, update both repos in the same change window.
4. If you add a new project, update the deploy mapping, the Terraform pipeline file, and the runtime workflow contract together.

---

Prepared by comparing the current integration and infra repos against the rock-style monorepo pattern.
