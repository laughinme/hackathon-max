"""A tiny stand-in for a management company's CRM, to show the integration loop.

    DOMOVOY_API_KEY=dmv_... PYTHONPATH=src uv run python -m scripts.mock_crm

On start it maps its status codes and registers its webhook with «Домовой»;
then it takes signed events, gives every new ticket its own number
(«АДС-…», returned in the answer, so the two numbers get linked) and shows a
page at http://localhost:8200 with buttons that send its statuses back. The
resident sees each press in MAX. Test data only.

Environment: DOMOVOY_API (default http://localhost:8080/integration/v1),
MOCK_CRM_PUBLIC_URL (where «Домовой» reaches this service, default
http://localhost:8200), MOCK_CRM_PORT (8200). A local backend needs
INTEGRATIONS_ALLOW_PRIVATE_URLS=true to call an http://localhost webhook.
"""

from __future__ import annotations

import contextlib
import html
import itertools
import os
import time
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from infrastructure.integrations.signature import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    verify,
)

API = os.getenv("DOMOVOY_API", "http://localhost:8080/integration/v1").rstrip("/")
API_KEY = os.getenv("DOMOVOY_API_KEY", "")
PUBLIC_URL = os.getenv("MOCK_CRM_PUBLIC_URL", "http://localhost:8200").rstrip("/")
PORT = int(os.getenv("MOCK_CRM_PORT", "8200"))

#: The CRM's own codes; «Домовой» learns them once through the status map.
STATUS_MAP = {
    "NEW": "registered",
    "ACCEPTED": "acknowledged",
    "WORKING": "in_progress",
    "DONE": "done",
    "CANCELLED": "rejected",
}
BUTTONS = (("ACCEPTED", "Принять"), ("WORKING", "В работу"), ("DONE", "Выполнено"))

#: Restarts must not reuse numbers: a record id belongs to one ticket.
numbers = itertools.count(int(time.time()) % 1_000_000)
tickets: dict[str, dict[str, Any]] = {}  # by our record id
seen_events: set[str] = set()
state: dict[str, str] = {}


async def call(method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with (
        aiohttp.ClientSession() as session,
        session.request(method, f"{API}{path}", json=body, headers=headers) as resp,
    ):
        payload = await resp.json()
        if resp.status >= 400:
            raise HTTPException(resp.status, payload)
        return payload


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    if not API_KEY:
        raise SystemExit("Set DOMOVOY_API_KEY (the dispatcher issues it)")
    await call("PUT", "/status-map", {"map": STATUS_MAP})
    hook = await call("PUT", "/webhook", {"url": f"{PUBLIC_URL}/webhook"})
    state["secret"] = hook["secret"]
    print(f"Mock CRM: webhook {hook['url']} registered, page {PUBLIC_URL}/")
    yield


app = FastAPI(title="Mock CRM (тестовые данные)", lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request) -> dict[str, Any]:
    body = await request.body()
    if not verify(
        state.get("secret", ""),
        request.headers.get(TIMESTAMP_HEADER, ""),
        body,
        request.headers.get(SIGNATURE_HEADER, ""),
        now=time.time(),
    ):
        raise HTTPException(401, "bad signature")
    event = await request.json()
    if event["id"] in seen_events or event["type"] == "ping":  # at-least-once
        return {}
    seen_events.add(event["id"])
    ticket = event["ticket"]
    record_id = (ticket.get("external") or {}).get("id")
    if record_id is None:
        record_id = str(next(numbers))
    tickets[record_id] = {**ticket, "last_event": event["type"]}
    print(f"<- {event['type']} {ticket['number']} -> АДС-{record_id}")
    return {"external_id": record_id, "external_number": f"АДС-{record_id}"}


@app.post("/tickets/{record_id}/{code}")
async def press(record_id: str, code: str) -> RedirectResponse:
    comment = {"WORKING": "Мастер выехал", "DONE": "Работы выполнены"}.get(code)
    result = await call(
        "POST",
        f"/tickets/ext:{record_id}/status",
        {"status": code, "comment": comment},
    )
    tickets[record_id] = {**result["ticket"], "last_event": f"-> {code}"}
    return RedirectResponse("/", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def page() -> str:
    rows = "".join(_row(record_id, t) for record_id, t in reversed(tickets.items()))
    return f"""<!doctype html><meta charset="utf-8"><meta http-equiv="refresh"
content="5"><title>Mock CRM</title><style>body{{font:15px system-ui;margin:24px}}
td,th{{padding:6px 10px;border-bottom:1px solid #ddd;text-align:left}}</style>
<h2>Mock CRM управляющей организации <small>(тестовые данные)</small></h2>
<table><tr><th>Наш №</th><th>№ Домового</th><th>Адрес</th><th>Проблема</th>
<th>Срок</th><th>Статус</th><th></th></tr>{rows}</table>"""


def _row(record_id: str, ticket: dict[str, Any]) -> str:
    buttons = "".join(
        f'<form method="post" action="/tickets/{record_id}/{code}" '
        f'style="display:inline"><button>{title}</button></form>'
        for code, title in BUTTONS
    )
    status = ticket.get("crm_status") or ticket["status"]
    return (
        f"<tr><td>АДС-{record_id}</td><td>{ticket['number']}</td>"
        f"<td>{html.escape(ticket['building']['address'])}</td>"
        f"<td>{html.escape(ticket['description'][:80])}</td>"
        f"<td>{ticket['deadlines']['resolve_by'][:16]}</td>"
        f"<td>{status}</td><td>{buttons}</td></tr>"
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
