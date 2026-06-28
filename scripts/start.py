#!/usr/bin/env python3
"""Start local dev stack from the monorepo root.

One command to bring up Docker (Postgres + Mailpit), apply migrations, and run
the API + webapp. Paths are resolved from the repo root — no machine-specific
locations required.

Usage (from anywhere, or from repo root):

    python scripts/start.py

Or:

    npm start

Equivalent to ``python scripts/dev.py run --target both`` (see ``npm run dev``).

Requires: Docker Desktop, Python 3.11+, Node 18+. Run ``python scripts/setup.py``
once if ``api/.venv`` or ``webapp/node_modules`` are missing.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV = REPO_ROOT / "scripts" / "dev.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Alma Lead Intake locally")
    parser.add_argument("--skip-docker", action="store_true", help="Do not run docker compose up")
    parser.add_argument("--skip-migrate", action="store_true", help="Skip alembic upgrade head")
    parser.add_argument("--skip-webapp", action="store_true", help="Start API only")
    parser.add_argument("--no-install-check", action="store_true", help="Skip venv/npm presence check")
    args = parser.parse_args()

    target = "api" if args.skip_webapp else "both"
    cmd = [sys.executable, str(DEV), "run", "--target", target]
    if args.skip_docker:
        cmd.append("--skip-docker")
    if args.skip_migrate:
        cmd.append("--skip-migrate")
    if args.no_install_check:
        cmd.append("--no-install-check")

    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
