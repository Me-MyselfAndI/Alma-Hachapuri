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


def main() -> None:
    api = REPO_ROOT / "api"
    webapp = REPO_ROOT / "webapp"
    venv = api / ".venv"

    if not venv.is_dir():
        _run([sys.executable, "-m", "venv", str(venv)], cwd=api)

    if sys.platform == "win32":
        py = venv / "Scripts" / "python.exe"
        pip = venv / "Scripts" / "pip.exe"
    else:
        py = venv / "bin" / "python"
        pip = venv / "bin" / "pip"

    _run([str(pip), "install", "-r", "requirements.txt"], cwd=api)

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

    print("\nSetup complete. Start the app with:  python scripts/start.py")


if __name__ == "__main__":
    main()
