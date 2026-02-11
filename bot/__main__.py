"""Entry point: python -m bot --db aurelm.db [--port 8473]"""

from __future__ import annotations

import argparse
import asyncio

from .config import load_config
from .main import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Aurelm Bot (Discord + HTTP)")
    parser.add_argument("--db", required=True, help="Path to aurelm.db")
    parser.add_argument("--port", type=int, default=None, help="HTTP server port (default: from config or 8473)")
    args = parser.parse_args()

    config = load_config(args.db, port_override=args.port)
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
