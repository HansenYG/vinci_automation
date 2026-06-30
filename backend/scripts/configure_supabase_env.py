"""Write Supabase URL/keys into backend/.env and frontend/.env from the linked CLI project."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_REF = "httraummzsnzabomibof"
ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = ROOT / "backend" / ".env"
FRONTEND_ENV = ROOT / "frontend" / ".env"


def _set_env(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = rf"^{re.escape(key)}=.*$"
    line = f"{key}={value}"
    if re.search(pattern, text, flags=re.MULTILINE):
        text = re.sub(pattern, line, text, count=1, flags=re.MULTILINE)
    else:
        text = text.rstrip() + f"\n{line}\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    proc = subprocess.run(
        ["supabase", "projects", "api-keys", "--project-ref", PROJECT_REF, "-o", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
        return proc.returncode

    keys = {item["name"]: item["api_key"] for item in json.loads(proc.stdout)}
    anon = keys.get("anon")
    service = keys.get("service_role")
    if not anon or not service:
        print("Could not find anon/service_role keys in CLI output.", file=sys.stderr)
        return 1

    url = f"https://{PROJECT_REF}.supabase.co"
    _set_env(BACKEND_ENV, "SUPABASE_URL", url)
    _set_env(BACKEND_ENV, "SUPABASE_KEY", service)
    _set_env(FRONTEND_ENV, "VITE_SUPABASE_URL", url)
    _set_env(FRONTEND_ENV, "VITE_SUPABASE_ANON_KEY", anon)

    print(f"Updated {BACKEND_ENV.name} and {FRONTEND_ENV.name} for project {PROJECT_REF}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
