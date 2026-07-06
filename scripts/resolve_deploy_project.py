#!/usr/bin/env python3

import argparse
import os
import sys


PROJECT_SETTINGS = {
    "dbt_airflow_test": {
        "DBT_PROJECT_DIR": "dbt_airflow_test",
        "IMAGE_NAME": "dbt_test",
        "JOB_NAME": "dbt-test-job-c-run",
        "DBT_MODEL_SELECTOR": "customer_seed_view customer_seed_view_test",
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
