#!/usr/bin/env python3

# Used by .github/workflows/dbt_deploy.yml to map the selected project
# input to deploy environment variables. Keep PROJECT_SETTINGS in sync
# with workflow project options.

import argparse
import os
import sys


PROJECT_SETTINGS = {
    "dbt_airflow_test": {
        "DBT_PROJECT_DIR": "dbt_airflow_test",
        "IMAGE_NAME": "dbt_test_job1",
        "JOB_NAME": "dbttest-job1",
        "WORKFLOW_NAME": "dbttest-orchestrator-job1",
        "DBT_MODEL_SELECTOR": "customer_seed_view customer_seed_view_test",
    },
    "dbt_project_2": {
        "DBT_PROJECT_DIR": "dbt_project_2",
        "IMAGE_NAME": "dbt_image_2",
        "JOB_NAME": "dbttest-job2",
        "WORKFLOW_NAME": "dbttest-orchestrator-job2",
        "DBT_MODEL_SELECTOR": "test_proj_2",
    }
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve deploy environment variables for a dbt project")
    parser.add_argument("--project", required=True, help="Project key from workflow input")
    args = parser.parse_args()

    settings = PROJECT_SETTINGS.get(args.project)
    if settings is None:
        print(f"Unknown project: {args.project}", file=sys.stderr)
        print(f"Available projects: {', '.join(sorted(PROJECT_SETTINGS.keys()))}", file=sys.stderr)
        return 1

    github_env = os.getenv("GITHUB_ENV")
    if not github_env:
        for key, value in settings.items():
            print(f"{key}={value}")
        return 0

    with open(github_env, "a", encoding="utf-8") as handle:
        for key, value in settings.items():
            handle.write(f"{key}={value}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
