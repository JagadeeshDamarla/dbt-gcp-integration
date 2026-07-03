# Architecture Drift Summary: current setup vs rock_logistics

## Scope compared
- Current setup:
  - dbt-gcp-integration (app/image/dbt code, Cloud Run job image update)
  - dbt-gcp-infra (Terraform infra ownership)
- Reference setup:
  - rock_logistics_inbound-main (single monorepo with app + infra + CI and many pipelines)

## High-level architecture snapshots

### Current setup (yours)
- Two-repo split:
  - App repo builds/pushes image and updates existing Cloud Run Job image.
  - Infra repo owns Terraform resources (Cloud Run Job, Workflows, IAM, APIs, secrets references).
- Workflow ownership intentionally separated to avoid overlap.
- Infra pipeline currently optimized for manual dispatch and safer execution in limited-permission CI.

### rock_logistics setup
- Single monorepo contains:
  - custom pipelines, multiple dbt projects, local run scripts, CI workflows, Terraform stacks.
- Terraform segmented into stage folders (`10_base_config`, `20_base_infrastructure`, `30_pipelines`, `40_dbt_pipelines`, etc.).
- Deploy flow can build one selected pipeline and then apply infra stacks from same repo.
- Strong reuse via Terraform modules for pipeline jobs, scheduler, workflows, secrets, and service accounts.

## Drift identified (what differs materially)

1. Repo boundary and ownership model
- Current: clean app/infra split across two repos.
- rock_logistics: single monorepo, app and infra tightly co-located.

2. Deployment coupling
- Current: app deploy updates image only; infra deploy owns resource lifecycle.
- rock_logistics: build and infra deploy are orchestrated together in repo workflows.

3. Scale model
- Current: focused setup for one dbt project/job pattern.
- rock_logistics: platform style with many pipeline definitions and per-pipeline tf files.

4. Terraform topology
- Current: environment-root modules in separate infra repo.
- rock_logistics: layered stack folders with shared constants and environment/project selection scripts.

5. Scheduling/orchestration style
- Current: Workflow orchestration exists, but pipeline shape is simpler.
- rock_logistics: both Cloud Scheduler -> Cloud Run and Scheduler -> Workflow patterns are used, including multi-schedule support and runtime tag injection.

6. IAM and bootstrap handling
- Current: explicit friction surfaced in CI permissions (service usage + IAM policy update), with safety toggles.
- rock_logistics: assumes stronger pre-provisioned IAM baseline and custom roles; CI appears integrated with that baseline.

7. Runtime standardization
- Current: one dbt project container pattern currently.
- rock_logistics: standardized env injection (`PROJECT_ID`, `TEAM`, `OTTO_ID`, secrets) and moduleized Cloud Run runtime settings across many jobs.

## Pros and cons of both approaches

### Current split-repo approach (your model)
Pros
- Clear separation of concerns (infra lifecycle vs app lifecycle).
- Lower blast radius from app changes; infra drift is easier to reason about.
- Better governance path for regulated environments (approval boundaries by repo).
- Easier to enforce least privilege in CI per repo purpose.

Cons
- Requires strict contract management between repos (names, regions, job/workflow ids, secrets).
- Higher operational coordination overhead.
- Bootstrap failures (API/IAM/backend) can be harder to debug across repo boundaries.
- Risk of temporary mismatch if one repo changes and the other lags.

### rock_logistics monorepo + layered stacks approach
Pros
- Fast delivery and discoverability: infra/app/scripts/workflows in one place.
- Strong reuse via modules and stage-based terraform structure.
- Easier bulk operations across many pipelines.
- Lower coordination cost when one team owns full platform codebase.

Cons
- Tighter coupling; app and infra changes can affect each other more directly.
- Larger blast radius for mistakes.
- Harder permission segmentation if many contributors touch same repo.
- CI/CD complexity can grow quickly with many pipelines and matrixed deploy paths.

## What you are already doing well
- You moved to explicit ownership split (good for scale/governance).
- You removed overlapping workflow deployment from app repo.
- You added fail-fast validation in infra CI (backend vars/service checks).
- You introduced safe feature toggles for IAM management where permissions are constrained.

## Suggested target state (best of both)

1. Keep two-repo ownership model.
2. Adopt rock-style module standardization patterns for multi-pipeline growth:
- reusable pipeline module inputs for schedule, secrets, runtime env, resources.
3. Create a versioned contract file shared by both repos (single source of truth for):
- project_id, region, artifact repository, job names, workflow names, secret ids.
4. Export required values from infra Terraform outputs and sync into app repo variables automatically.
5. Introduce environment promotion flow:
- infra apply -> app image deploy -> workflow execution smoke checks.

## Practical migration checklist from here

1. Add additional dbt job definitions in infra using reusable module blocks.
2. Keep app repo workflow image-only and job-update-only per repo.
3. Add one orchestrator workflow input schema for runtime model selectors/vars.
4. Automate repo variable sync from infra outputs.
5. Add policy guardrails:
- CI permissions by responsibility, and separate IAM-admin apply path.

---
Prepared by comparing:
- rock_logistics_inbound-main workflows, terraform stages/modules, and pipeline scheduling patterns
- dbt-gcp-integration + dbt-gcp-infra current split architecture and recent CI/Terraform alignment changes
