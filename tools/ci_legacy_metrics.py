"""Read-only legacy baseline: ruff/black debt report."""

import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUFF_EXCLUDE = "tools/archive,old,models,data"
BLACK_EXCLUDE = r"(tools/archive|old|models|data|\.pytest_cache|_tmp|dist|build|node_modules|legacy_verify|\.git)"


def _run(cmd):
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="ignore")


def main():
    r = _run(
        [sys.executable, "-X", "utf8", "-B", "-m", "ruff", "check", ".", "--exclude", RUFF_EXCLUDE, "--statistics"]
    )
    m = re.search(r"Found (\d+) errors", r.stdout + r.stderr)
    total = int(m.group(1)) if m else None
    b = _run([sys.executable, "-X", "utf8", "-B", "-m", "black", "--check", ".", "--exclude", BLACK_EXCLUDE])
    n = len([ln for ln in (b.stdout + b.stderr).splitlines() if "would reformat" in ln])
    print(
        json.dumps(
            {
                "captured_at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
                "ruff": {"errors": total, "rc": r.returncode},
                "black": {"would_reformat": n, "rc": b.returncode},
                "note": "legacy advisory only; no --fix/black shortcut",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
