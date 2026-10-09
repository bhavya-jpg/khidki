"""Cache real Delhi outdoor air for 2025 school days (Mon to Fri, 15 Oct to 20 Dec) as replay fixtures.

Two requests for the whole range (CAMS air quality + weather archive), split into one JSON per day.
Usage: python tasks.py fetch-replay [--start 2025-10-15] [--end 2025-12-20]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from khidki_data.openmeteo import ATTRIBUTION, air_quality, weather
from khidki_data.replay import DEMO_LAT, DEMO_LON, FIXTURES


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-10-15")
    ap.add_argument("--end", default="2025-12-20")
    args = ap.parse_args(argv)
    print(f"Fetching CAMS air quality and weather for East Delhi, {args.start} to {args.end}...")
    aq = air_quality(DEMO_LAT, DEMO_LON, start_date=args.start, end_date=args.end, timeout_s=90)
    wx = weather(DEMO_LAT, DEMO_LON, start_date=args.start, end_date=args.end, timeout_s=90)
    both = aq.merge(wx)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    day = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    n = 0
    while day <= end:
        if day.weekday() < 5:
            d = both.day(day.isoformat())
            if len(d.time) == 24 and all(v is not None for v in d.values["pm2_5"]):
                (FIXTURES / f"{day.isoformat()}.json").write_text(
                    json.dumps(d.to_json(), separators=(",", ":"))
                )
                n += 1
        day += dt.timedelta(days=1)
    (FIXTURES / "ATTRIBUTION.txt").write_text(
        f"{ATTRIBUTION}\nLocation: {DEMO_LAT}, {DEMO_LON} (East Delhi). "
        f"Fetched {dt.date.today().isoformat()}.\n"
        "These are model values (CAMS global, ~45 km), not station measurements.\n"
    )
    print(f"Wrote {n} replay days to {FIXTURES}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
