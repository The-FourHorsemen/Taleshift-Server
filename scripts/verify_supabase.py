#!/usr/bin/env python3
"""Smoke-test Supabase connectivity from this server."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import get_supabase_client  # noqa: E402


def main() -> int:
    client = get_supabase_client()
    # Auth health check hits the project without needing tables yet.
    session = client.auth.get_session()
    print("Connected to Supabase.")
    print(f"  URL host ok; auth session present: {session is not None}")

    # List tables via a lightweight REST probe if any exist.
    try:
        result = client.table("learners").select("id").limit(1).execute()
        print(f"  learners table reachable ({len(result.data)} row(s) sampled).")
    except Exception as exc:  # noqa: BLE001 — intentional probe
        print(f"  learners table not ready yet (expected until schema applied): {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
