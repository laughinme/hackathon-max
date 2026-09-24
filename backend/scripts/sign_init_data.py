"""Signed MAX launch data for calling the REST API without MAX (DATA-API.yaml).

    MAX_TOKEN=... PYTHONPATH=src python -m scripts.sign_init_data --user-id -100

Prints the value for the `Authorization` header: `tma <initData>`. It is valid
for one hour (the server rejects older auth_date). The token is read from the
environment and never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import time

from infrastructure.max.init_data import sign_init_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Sign MAX initData for tests")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--name", default="Проверяющий")
    args = parser.parse_args()

    token = os.environ.get("MAX_TOKEN")
    if not token:
        raise SystemExit("Set MAX_TOKEN in the environment (see backend/.env)")
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "checker",
        "user": json.dumps({"id": args.user_id, "first_name": args.name}),
    }
    print(f"tma {sign_init_data(fields, token)}")


if __name__ == "__main__":
    main()
