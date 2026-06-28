#!/usr/bin/env python3
"""One-time local dev setup from the monorepo root.

Creates ``api/.venv``, installs Python deps, and ``npm install`` in webapp/.
Paths are relative to the repo root — clone anywhere and run:

    python scripts/setup.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], *, cwd: Path) -> None:
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def _venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _venv_usable(py: Path) -> bool:
    if not py.is_file():
        return False
    result = subprocess.run(
        [str(py), "-m", "pip", "--version"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _ensure_venv(venv: Path, *, cwd: Path) -> Path:
    py = _venv_python(venv)
    if venv.is_dir() and not _venv_usable(py):
        print(f"Removing stale venv at {venv.relative_to(REPO_ROOT)} (broken pip/python paths)")
        shutil.rmtree(venv)
    if not venv.is_dir():
        _run([sys.executable, "-m", "venv", str(venv)], cwd=cwd)
    return _venv_python(venv)


def main() -> None:
    api = REPO_ROOT / "api"
    webapp = REPO_ROOT / "webapp"
    venv = api / ".venv"

    py = _ensure_venv(venv, cwd=api)
    # Use ``python -m pip`` — avoids broken pip.exe launchers after folder renames.
    _run([str(py), "-m", "pip", "install", "-r", "requirements.txt"], cwd=api)

    env_example = REPO_ROOT / ".env.example"
    env_file = REPO_ROOT / ".env"
    if env_example.is_file() and not env_file.is_file():
        shutil.copy(env_example, env_file)
        print(f"Created {env_file.relative_to(REPO_ROOT)} from .env.example")

    webapp_env = webapp / ".env.local"
    if not webapp_env.is_file():
        webapp_env.write_text(
            "NEXT_PUBLIC_API_URL=http://localhost:8000\n",
            encoding="utf-8",
        )
        print(f"Created {webapp_env.relative_to(REPO_ROOT)}")

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    _run([npm, "install"], cwd=webapp)

    print("\nSetup complete. Start the app with:  python scripts/dev.py run --target all")


if __name__ == "__main__":
    main()
