#!/usr/bin/env python3
"""Start local dev stack from the monorepo root.

One command to bring up Docker (Postgres + Mailpit), apply migrations, and run
the API + webapp. Paths are resolved from the repo root — no machine-specific
locations required.

Usage (from anywhere, or from repo root):

    python scripts/start.py

Or:

    npm start

Requires: Docker Desktop, Python 3.11+, Node 18+. Run ``python scripts/setup.py``
once if ``api/.venv`` or ``webapp/node_modules`` are missing.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PROJECT_ROOT", str(REPO_ROOT))

PROCS: list[subprocess.Popen] = []


def _api_python() -> Path:
    venv = REPO_ROOT / "api" / ".venv"
    if sys.platform == "win32":
        candidate = venv / "Scripts" / "python.exe"
    else:
        candidate = venv / "bin" / "python"
    if candidate.is_file():
        return candidate
    return Path(sys.executable)


def _run(cmd: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    print(f"+ {' '.join(cmd)}  (cwd={cwd.relative_to(REPO_ROOT)})")
    return subprocess.run(cmd, cwd=cwd, check=check, env=_child_env())


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(REPO_ROOT)
    return env


def _spawn(cmd: list[str], *, cwd: Path) -> subprocess.Popen:
    print(f"+ {' '.join(cmd)}  (cwd={cwd.relative_to(REPO_ROOT)})")
    kwargs: dict = {"cwd": cwd, "env": _child_env()}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    return subprocess.Popen(cmd, **kwargs)


def _shutdown(_signum=None, _frame=None) -> None:
    print("\nStopping child processes…")
    for proc in PROCS:
        if proc.poll() is None:
            proc.terminate()
    for proc in PROCS:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    sys.exit(0)


def _ensure_prereqs() -> None:
    py = _api_python()
    venv_marker = REPO_ROOT / "api" / ".venv"
    if not venv_marker.is_dir():
        print("Missing api/.venv — run:  python scripts/setup.py", file=sys.stderr)
        sys.exit(1)
    if shutil.which("npm") is None:
        print("npm not found on PATH — install Node.js", file=sys.stderr)
        sys.exit(1)
    if shutil.which("docker") is None:
        print("docker not found on PATH — install Docker Desktop", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Alma Lead Intake locally")
    parser.add_argument("--skip-docker", action="store_true", help="Do not run docker compose up")
    parser.add_argument("--skip-migrate", action="store_true", help="Skip alembic upgrade head")
    parser.add_argument("--skip-webapp", action="store_true", help="Start API only")
    parser.add_argument("--no-install-check", action="store_true", help="Skip venv/npm presence check")
    args = parser.parse_args()

    if not args.no_install_check:
        _ensure_prereqs()

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    py = _api_python()

    if not args.skip_docker:
        _run(["docker", "compose", "up", "-d"], cwd=REPO_ROOT)
        time.sleep(2)

    if not args.skip_migrate:
        _run([str(py), "-m", "alembic", "upgrade", "head"], cwd=REPO_ROOT / "db")

    PROCS.append(
        _spawn(
            [str(py), "-m", "uvicorn", "src.main:app", "--reload", "--port", "8000"],
            cwd=REPO_ROOT / "api",
        )
    )

    if not args.skip_webapp:
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        PROCS.append(_spawn([npm, "run", "dev"], cwd=REPO_ROOT / "webapp"))

    print()
    print("Running:")
    print("  API      http://localhost:8000  (docs: /docs)")
    print("  Mailpit  http://localhost:8025")
    if not args.skip_webapp:
        print("  Webapp   http://localhost:3000")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            for proc in PROCS:
                code = proc.poll()
                if code is not None:
                    print(f"Process exited with code {code}", file=sys.stderr)
                    _shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()
