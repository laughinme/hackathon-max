"""Run the mandatory API checks from DATA-API.yaml against a deployment.

    MAX_TOKEN=... PYTHONPATH=src python -m scripts.check_api https://host

Checks status codes and `error_code` of every check, in file order (some of
them change the test tickets: reset them first, see `fixtures.reset`).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from infrastructure.max.init_data import sign_init_data

SPEC = Path(__file__).resolve().parents[2] / "DATA-API.yaml"


def _auth(role: str, accounts: dict[str, Any], token: str) -> dict[str, str]:
    if role == "none":
        return {}
    user_id = accounts["resident" if role == "forged" else role]["user_id"]
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "check-api",
        "user": json.dumps({"id": user_id, "first_name": "Проверка"}),
    }
    signed = sign_init_data(fields, token)
    if role == "forged":
        signed = signed.replace("check-api", "check-apj")
    return {"Authorization": f"tma {signed}"}


def _call(
    base: str, method: str, path: str, headers: dict[str, str], body: Any
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={**headers, **({"Content-Type": "application/json"} if data else {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        raw, status = error.read(), error.code
    try:
        parsed = json.loads(raw) if raw else {}
    except ValueError:
        parsed = {}
    return status, parsed if isinstance(parsed, dict) else {"items": parsed}


Call = Callable[[str, str, dict[str, str], Any], tuple[int, dict[str, Any]]]


def run_checks(call: Call, token: str) -> list[tuple[dict[str, Any], int, bool]]:
    """(check, status, passed) for every check of DATA-API.yaml, in order."""

    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    fixtures = {k: v for k, v in spec["fixtures"].items() if k != "reset"}
    results = []
    for check in spec["checks"]:
        role = str(check["role"]).split()[0]
        status, body = call(
            check["method"],
            check["path"].format(**fixtures),
            _auth(role, spec["accounts"], token),
            check.get("body"),
        )
        expected = check["expect"]
        ok = status == expected["status"]
        if ok and "error_code" in expected:
            ok = body.get("error_code") == expected["error_code"]
        results.append((check, status, ok))
    return results


def main() -> int:
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8080"
    token = os.environ.get("MAX_TOKEN")
    if not token:
        raise SystemExit("Set MAX_TOKEN (see backend/.env)")
    results = run_checks(
        lambda method, path, headers, body: _call(base, method, path, headers, body),
        token,
    )
    for check, status, ok in results:
        print(f"{'✅' if ok else '❌'} {check['id']:>2}. {check['title']}: {status}")
    passed = sum(ok for _, _, ok in results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
