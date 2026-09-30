"""Issue an API key of the integration API for a dispatcher's company.

    DATABASE_URL=... PYTHONPATH=src python -m scripts.integration_key \\
        --dispatcher <max_user_id> [--name "1С:Жилищный стандарт"]

The same as the dispatcher's button in the mini-app (POST
/api/v1/dispatcher/integrations), for operators and local runs. The key is
printed once; only its hash is stored.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from application.integrations.connect_integration import ConnectIntegration
from infrastructure.clock import SystemClock
from infrastructure.db.engine import make_engine, make_session_factory
from infrastructure.db.uow import SqlUnitOfWork


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dispatcher", type=int, required=True)
    parser.add_argument("--name", default="CRM")
    args = parser.parse_args()

    engine = make_engine(os.environ["DATABASE_URL"])
    try:
        session_factory = make_session_factory(engine)
        connect = ConnectIntegration(
            lambda: SqlUnitOfWork(session_factory), SystemClock()
        )
        connected = await connect.execute(args.dispatcher, args.name)
    finally:
        await engine.dispose()
    print(f"Integration {connected.integration.name} ({connected.integration.id})")
    print(f"API key (shown once): {connected.api_key}")
    print("Docs: https://<host>/integration/v1/docs")


if __name__ == "__main__":
    asyncio.run(main())
