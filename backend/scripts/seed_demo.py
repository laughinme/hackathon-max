"""Load the synthetic demo dataset into PostgreSQL (safe to run repeatedly).

Usage: DATABASE_URL=... PYTHONPATH=src python -m scripts.seed_demo
       ... python -m scripts.seed_demo --reset-test-accounts   # before re-running
                                                           # DATA-API.yaml checks
"""

from __future__ import annotations

import asyncio
import os
import sys

from infrastructure.clock import SystemClock
from infrastructure.db.engine import make_engine, make_session_factory
from infrastructure.db.uow import SqlUnitOfWork
from infrastructure.seed.demo_data import build_demo_dataset
from infrastructure.seed.loaders import load_into_postgres
from infrastructure.seed.test_accounts import ensure_test_accounts, reset_test_tickets


async def main() -> None:
    engine = make_engine(os.environ["DATABASE_URL"])
    try:
        clock = SystemClock()
        session_factory = make_session_factory(engine)
        dataset = build_demo_dataset(clock.now())
        written = await load_into_postgres(session_factory, dataset)
        if "--reset-test-accounts" in sys.argv:
            await reset_test_tickets(session_factory)
        tests = await ensure_test_accounts(
            lambda: SqlUnitOfWork(session_factory), clock
        )
    finally:
        await engine.dispose()
    if written:
        print(
            f"Demo data loaded: {len(dataset.buildings)} buildings, "
            f"{len(dataset.tickets)} tickets"
        )
    else:
        print("Demo data already present, nothing to do")
    print(f"Test accounts for DATA-API.yaml ready ({tests} tickets created now)")


if __name__ == "__main__":
    asyncio.run(main())
