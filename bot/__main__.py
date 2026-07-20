"""Entry point: python -m bot --db aurelm.db [--port 8473]"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .config import load_config
from .main import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Aurelm Bot (Discord + HTTP)")
    parser.add_argument("--db", required=True, help="Path to aurelm.db")
    parser.add_argument("--port", type=int, default=None, help="HTTP server port (default: from config or 8473)")
    # WHY a dedicated mode: the first-run wizard must guarantee the full schema
    # exists BEFORE the app mounts, because Flutter's Drift layer only creates a few
    # of its own tables — the ~35 core tables are owned by these migrations. Starting
    # the whole bot (Discord gateway, HTTP server) just to migrate would be wasteful
    # and racy; this applies migrations and exits, so the wizard can await a clean
    # exit code before pointing the app at the DB.
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Apply DB migrations and exit (used by the first-run wizard).",
    )
    args = parser.parse_args()

    if args.migrate_only:
        from .migrations import apply_migrations

        try:
            apply_migrations(args.db)
        except Exception as exc:  # missing bundle dir, unwritable path, bad SQL
            print(f"migration failed: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"migrations applied: {args.db}")
        sys.exit(0)

    config = load_config(args.db, port_override=args.port)
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
