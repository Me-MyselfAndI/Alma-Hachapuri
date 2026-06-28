#!/usr/bin/env python3
"""Unified dev CLI: run, test, and build for api + webapp from repo root."""

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


def _npm_cmd() -> str:
    return "npm.cmd" if sys.platform == "win32" else "npm"


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(REPO_ROOT)
    return env


def _run(cmd: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    print(f"+ {' '.join(cmd)}  (cwd={cwd.relative_to(REPO_ROOT)})")
    return subprocess.run(cmd, cwd=cwd, check=check, env=_child_env())


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


def _ensure_run_prereqs(target: str, *, no_install_check: bool) -> None:
    if no_install_check:
        return
    if target in ("api", "both"):
        if not (REPO_ROOT / "api" / ".venv").is_dir():
            print("Missing api/.venv — run:  python scripts/setup.py", file=sys.stderr)
            sys.exit(1)
        if shutil.which("docker") is None:
            print("docker not found on PATH — install Docker Desktop", file=sys.stderr)
            sys.exit(1)
    if target in ("webapp", "both"):
        if shutil.which("npm") is None:
            print("npm not found on PATH — install Node.js", file=sys.stderr)
            sys.exit(1)


def _ensure_api_venv(*, label: str = "test") -> None:
    if not (REPO_ROOT / "api" / ".venv").is_dir():
        print(f"Missing api/.venv — run setup before {label}", file=sys.stderr)
        sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    target = args.target
    _ensure_run_prereqs(target, no_install_check=args.no_install_check)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    if target in ("api", "both"):
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

    if target in ("webapp", "both"):
        PROCS.append(_spawn([_npm_cmd(), "run", "dev"], cwd=REPO_ROOT / "webapp"))

    print()
    print("Running:")
    if target in ("api", "both"):
        print("  API      http://localhost:8000  (docs: /docs)")
        print("  Mailpit  http://localhost:8025")
    if target in ("webapp", "both"):
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


def _run_checked(cmd: list[str], *, cwd: Path) -> int:
    print(f"+ {' '.join(cmd)}  (cwd={cwd.relative_to(REPO_ROOT)})")
    result = subprocess.run(cmd, cwd=cwd, env=_child_env())
    return result.returncode


def cmd_test(args: argparse.Namespace) -> int:
    target = args.target
    failed = False

    if target in ("api", "all"):
        _ensure_api_venv(label="api tests")
        py = _api_python()
        code = _run_checked([str(py), "-m", "pytest", "tst/", "-q"], cwd=REPO_ROOT / "api")
        if code != 0:
            failed = True

    if target in ("webapp", "all"):
        npm = _npm_cmd()
        webapp = REPO_ROOT / "webapp"
        for script in ("lint", "build"):
            code = _run_checked([npm, "run", script], cwd=webapp)
            if code != 0:
                failed = True

    return 1 if failed else 0


def cmd_build(args: argparse.Namespace) -> int:
    target = args.target
    failed = False

    if target in ("api", "all"):
        _ensure_api_venv(label="build")
        print("api: venv OK (no separate build step)")

    if target in ("webapp", "all"):
        code = _run_checked([_npm_cmd(), "run", "build"], cwd=REPO_ROOT / "webapp")
        if code != 0:
            failed = True

    return 1 if failed else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Alma Lead Intake — unified dev CLI (run, test, build)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Start dev processes")
    run_p.add_argument(
        "--target",
        choices=("api", "webapp", "both"),
        default="both",
        help="Which stack to start (default: both)",
    )
    run_p.add_argument("--skip-docker", action="store_true", help="Do not run docker compose up")
    run_p.add_argument("--skip-migrate", action="store_true", help="Skip alembic upgrade head")
    run_p.add_argument(
        "--no-install-check",
        action="store_true",
        help="Skip venv/npm/docker presence check",
    )
    run_p.set_defaults(func=cmd_run)

    test_p = sub.add_parser("test", help="Run test/lint/build checks")
    test_p.add_argument(
        "--target",
        choices=("api", "webapp", "all"),
        default="all",
        help="Which package to test (default: all)",
    )
    test_p.set_defaults(func=cmd_test)

    build_p = sub.add_parser("build", help="Production-style builds")
    build_p.add_argument(
        "--target",
        choices=("api", "webapp", "all"),
        default="all",
        help="Which package to build (default: all)",
    )
    build_p.set_defaults(func=cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    result = args.func(args)
    if isinstance(result, int):
        return result
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
