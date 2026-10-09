"""Call data.gov.in's real-time AQI resource once and report what comes back.

Needs DATAGOV_KEY (environment or .env). Prints status, record count, 3 sample records and the nearest PM2.5
station to the demo school, then appends the findings to docs/LEARNINGS.md. If the API is unavailable or
useless, bias correction stays r = 1 and the app says "uncorrected forecast".
Usage: python scripts/probe_cpcb.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

from khidki_data import cpcb
from khidki_data.http import FetchError, get_json
from khidki_data.replay import DEMO_LAT, DEMO_LON

ROOT = Path(__file__).resolve().parents[1]


def key() -> str | None:
    if os.environ.get("DATAGOV_KEY"):
        return os.environ["DATAGOV_KEY"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("DATAGOV_KEY=") and line.split("=", 1)[1].strip():
                return line.split("=", 1)[1].strip()
    return None


def main() -> int:
    k = key()
    if not k:
        print("No DATAGOV_KEY. Register at https://data.gov.in (free), add DATAGOV_KEY=... to .env, re-run.")
        print("Until then: bias correction stays r = 1 and the UI says 'uncorrected forecast'.")
        return 2
    params = {"api-key": k, "format": "json", "limit": 1000, "filters[city]": "Delhi"}
    try:
        payload = get_json(cpcb.RESOURCE_URL, params, timeout_s=30)
    except FetchError as exc:
        print(f"Request failed: {exc}")
        return 1
    records = payload.get("records", [])
    print(f"status: {payload.get('status')}, total: {payload.get('total')}, returned: {len(records)}")
    print("fields:", sorted(records[0].keys()) if records else "-")
    for r in records[:3]:
        print(json.dumps(r, ensure_ascii=False))
    readings = cpcb.parse_records(payload)
    hit = cpcb.nearest_pm25(readings, DEMO_LAT, DEMO_LON)
    if hit:
        print(f"nearest PM2.5: {hit[0].station} ({hit[1]:.1f} km) avg={hit[0].avg} at {hit[0].last_update}")
    note = (
        f"\n### CPCB probe, {dt.date.today().isoformat()}\n"
        f"data.gov.in returned {len(records)} Delhi records; fields: "
        f"{', '.join(sorted(records[0].keys())) if records else 'none'}. "
        + (
            f"Nearest PM2.5 station to the demo school: {hit[0].station}, {hit[1]:.1f} km, "
            f"avg {hit[0].avg} (last update {hit[0].last_update}). "
            if hit
            else "No PM2.5 station found. "
        )
        + "Check whether `avg_value` is a concentration or a sub-index before trusting the bias ratio.\n"
    )
    with (ROOT / "docs" / "LEARNINGS.md").open("a") as f:
        f.write(note)
    print("Findings appended to docs/LEARNINGS.md")
    return 0 if hit else 1


if __name__ == "__main__":
    sys.exit(main())
