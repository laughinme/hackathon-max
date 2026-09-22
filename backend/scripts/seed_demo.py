"""Load the synthetic demo dataset into PostgreSQL (safe to run repeatedly).

Usage: DATABASE_URL=... PYTHONPATH=src python -m scripts.seed_demo
"""

from __future__ import annotations

import asyncio
import os

from infrastructure.clock import SystemClock
from infrastructure.db.engine import make_engine, make_session_factory
from infrastructure.seed.demo_data import build_demo_dataset
from infrastructure.seed.loaders import load_into_postgres


async def main() -> None:
    engine = make_engine(os.environ["DATABASE_URL"])
    try:
        dataset = build_demo_dataset(SystemClock().now())
        written = await load_into_postgres(make_session_factory(engine), dataset)
    finally:
        await engine.dispose()
    if written:
        print(
            f"Demo data loaded: {len(dataset.buildings)} buildings, "
            f"{len(dataset.tickets)} tickets"
        )
    else:
        print("Demo data already present, nothing to do")


if __name__ == "__main__":
    asyncio.run(main())
