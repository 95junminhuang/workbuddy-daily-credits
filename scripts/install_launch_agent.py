#!/usr/bin/env python3
"""Install or remove a macOS LaunchAgent for zero-model daily claiming."""

from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path


LABEL = "com.workbuddy.daily-credits"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_PATH = Path.home() / ".workbuddy" / "logs" / "daily-credits.log"


def launchctl(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/bin/launchctl", *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def remove_loaded_job() -> None:
    domain = f"gui/{os.getuid()}"
    launchctl("bootout", domain, str(PLIST_PATH), check=False)


def uninstall() -> None:
    remove_loaded_job()
    try:
        PLIST_PATH.unlink()
    except FileNotFoundError:
        pass
    print(f"REMOVED label={LABEL}")


def install(hour: int, minute: int) -> None:
    claim_script = Path(__file__).resolve().with_name("claim_daily_credit.py")
    if not claim_script.is_file():
        raise SystemExit(f"claim script not found: {claim_script}")
    python = shutil.which("python3") or sys.executable
    if not python:
        raise SystemExit("python3 not found")

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": LABEL,
        "ProgramArguments": [python, str(claim_script), "--claim", "--json"],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "ProcessType": "Background",
        "RunAtLoad": False,
        "StandardOutPath": str(LOG_PATH),
        "StandardErrorPath": str(LOG_PATH),
        "EnvironmentVariables": {
            "HOME": str(Path.home()),
            "PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin",
        },
    }

    temp = PLIST_PATH.with_suffix(".plist.tmp")
    with temp.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)
    os.chmod(temp, 0o644)
    temp.replace(PLIST_PATH)

    remove_loaded_job()
    result = launchctl("bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH), check=False)
    if result.returncode != 0:
        # Compatibility fallback for older launchctl behavior.
        result = launchctl("load", str(PLIST_PATH), check=False)
    if result.returncode != 0:
        raise SystemExit(f"launchctl failed: {result.stderr.strip()}")
    print(f"INSTALLED label={LABEL} schedule={hour:02d}:{minute:02d} log={LOG_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install WorkBuddy daily-credit scheduling.")
    parser.add_argument("--hour", type=int, default=0)
    parser.add_argument("--minute", type=int, default=30)
    parser.add_argument("--uninstall", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.uninstall:
        uninstall()
        return 0
    if not 0 <= args.hour <= 23 or not 0 <= args.minute <= 59:
        raise SystemExit("hour must be 0-23 and minute must be 0-59")
    install(args.hour, args.minute)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
