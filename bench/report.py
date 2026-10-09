"""Turn bench/results into docs/benchmark.md, bench/results/pareto.png and web/public/benchmark.json.

Chart rules (dataviz method): one y-axis per panel, validated categorical palette (Khidki = slot 1,
CO₂ alarm = slot 2, other policies muted ink), direct labels, legend, recessive grid, text in ink colours.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "bench" / "results"
CHALK, INK, INK2, INK3, RULE = "#EEF0E6", "#1F3A30", "#3F564C", "#5A6C63", "#C9CFC2"
KHIDKI, ALARM = "#1C7DC0", "#C2661A"
NAMES = {
    "ALWAYS_CLOSED": "Always closed",
    "ALWAYS_OPEN": "Always open",
    "CO2_ALARM": "CO₂ alarm",
    "TEMPERATURE_TEACHER": "Temperature-led teacher",
    "KHIDKI": "Khidki",
    "KHIDKI_100": "Khidki, teacher always acts",
}
ROOM_TITLE = {
    "no_purifier": "Class without a purifier (44 children)",
    "purifier": "Class with a purifier (38 children)",
}


def load() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = json.loads((RESULTS / "summary.json").read_text())
    with (RESULTS / "rows.csv").open() as f:
        rows = [
            {k: (v if k in ("date", "room", "policy") else float(v)) for k, v in r.items()}
            for r in csv.DictReader(f)
        ]
    return summary, rows


def paired(rows: list[dict[str, Any]], room: str, a: str, b: str) -> dict[str, Any]:
    by = {(r["date"], r["policy"]): r for r in rows if r["room"] == room}
    dates = sorted({d for d, _ in by})
    co2_better = sum(by[(d, a)]["co2_min_over_1500"] < by[(d, b)]["co2_min_over_1500"] for d in dates)
    co2_tie = sum(by[(d, a)]["co2_min_over_1500"] == by[(d, b)]["co2_min_over_1500"] for d in dates)
    pm_diff = [
        (by[(d, a)]["pm_dose_ug"] - by[(d, b)]["pm_dose_ug"]) / by[(d, "ALWAYS_OPEN")]["pm_dose_ug"] * 100
        for d in dates
    ]
    req_ratio = [by[(d, a)]["requests"] / max(by[(d, b)]["requests"], 1) for d in dates]
    return {
        "days": len(dates),
        "co2_better_days": co2_better,
        "co2_tie_days": co2_tie,
        "median_pm_diff_pts": round(float(np.median(pm_diff)), 1),
        "median_request_ratio": round(float(np.median(req_ratio)), 2),
    }


def chart(summary: dict[str, Any]) -> Path:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.edgecolor": RULE,
            "axes.labelcolor": INK2,
            "xtick.color": INK2,
            "ytick.color": INK2,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), facecolor=CHALK)
    for ax, (room, r) in zip(axes, summary["rooms"].items(), strict=True):
        pols = r["policies"]
        ax.set_facecolor(CHALK)
        ax.grid(True, color=RULE, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for name in ("ALWAYS_CLOSED", "ALWAYS_OPEN", "TEMPERATURE_TEACHER"):
            k = pols[name]
            ax.scatter(
                k["pm_pct_of_always_open"],
                k["co2_min_over_1500"],
                s=60,
                color=INK3,
                zorder=3,
                edgecolors=CHALK,
                linewidths=2,
            )
            ax.annotate(
                NAMES[name],
                (k["pm_pct_of_always_open"], k["co2_min_over_1500"]),
                textcoords="offset points",
                xytext=(8, 4),
                color=INK2,
                fontsize=9,
            )
        sweep = ["KHIDKI", *sorted(p for p in pols if p.startswith("KHIDKI_a"))]
        xs = [pols[p]["pm_pct_of_always_open"] for p in sweep]
        ys = [pols[p]["co2_min_over_1500"] for p in sweep]
        ax.plot(xs, ys, color=KHIDKI, linewidth=2, zorder=2, label="Khidki, PM weight 0.5 → 0.9")
        ax.scatter(xs[1:], ys[1:], s=36, color=KHIDKI, zorder=4, edgecolors=CHALK, linewidths=2)
        k = pols["KHIDKI"]
        ax.scatter(
            k["pm_pct_of_always_open"],
            k["co2_min_over_1500"],
            s=110,
            color=KHIDKI,
            zorder=5,
            edgecolors=CHALK,
            linewidths=2,
            label="Khidki (Balanced)",
        )
        ax.annotate(
            f"Khidki, {k['requests']:.0f} requests/day",
            (k["pm_pct_of_always_open"], k["co2_min_over_1500"]),
            textcoords="offset points",
            xytext=(-14, -4),
            ha="right",
            color=INK,
            fontsize=9,
            fontweight="bold",
        )
        a = pols["CO2_ALARM"]
        ax.scatter(
            a["pm_pct_of_always_open"],
            a["co2_min_over_1500"],
            s=110,
            color=ALARM,
            marker="D",
            zorder=5,
            edgecolors=CHALK,
            linewidths=2,
            label="CO₂ alarm",
        )
        ax.annotate(
            f"CO₂ alarm, {a['requests']:.0f} requests/day",
            (a["pm_pct_of_always_open"], a["co2_min_over_1500"]),
            textcoords="offset points",
            xytext=(-14, 12),
            ha="right",
            color=INK,
            fontsize=9,
            fontweight="bold",
        )
        ax.set_title(ROOM_TITLE[room], color=INK, fontsize=11, loc="left")
        ax.set_xlabel("PM2.5 dose per child, % of an always-open room (lower is better)")
        ax.set_ylabel("Minutes above 1,500 ppm CO₂ per day (lower is better)")
        ax.set_xlim(30, 105)
        ax.set_ylim(-10, 290)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, labelcolor=INK2)
    fig.suptitle(
        "Mean over 48 school days. Simulated classroom, real Delhi outdoor air (CAMS, Oct to Dec 2025). "
        "Not a field trial.",
        color=INK2,
        fontsize=9,
        x=0.01,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    out = RESULTS / "pareto.png"
    fig.savefig(out, dpi=150, facecolor=CHALK)
    shutil.copy(out, ROOT / "docs" / "benchmark-pareto.png")
    return out


def markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Benchmark",
        "",
        f"> **{summary['label']}**",
        "",
        "Generated by `python tasks.py bench`. Every policy runs on the same true room (whose physics differ from the",
        "defaults Khidki plans with), at 1-minute resolution, over every cached school day. Khidki and the CO₂ alarm get",
        "the same teacher, who acts on a request 70% of the time after 1 to 3 minutes. Khidki re-plans every 30",
        "minutes and counts every request against its daily budget of 6, including ones the teacher ignored.",
        "",
        "![Pareto chart](benchmark-pareto.png)",
        "",
    ]
    for room, r in summary["rooms"].items():
        pols = r["policies"]
        lines += [
            f"## {ROOM_TITLE[room]}",
            "",
            "| Policy | PM2.5 dose (% of always open) | Min > 1,500 ppm | Min > 1,000 ppm | Peak CO₂ | Cold exposure (°C·min) | Requests to teacher |",
            "|---|---|---|---|---|---|---|",
        ]
        for p, k in pols.items():
            name = NAMES.get(p, p.replace("KHIDKI_a", "Khidki, PM weight "))
            lines.append(
                f"| {name} | {k['pm_pct_of_always_open']} | {k['co2_min_over_1500']} | {k['co2_min_over_1000']} | "
                f"{k['max_co2']} | {k['cold_deg_min']} | {k['requests']} |"
            )
        pr = paired(rows, room, "KHIDKI", "CO2_ALARM")
        lines += [
            "",
            f"**Khidki (Balanced) vs CO₂ alarm, day by day:** fewer minutes above 1,500 ppm on {pr['co2_better_days']} "
            f"of {pr['days']} days (tied on {pr['co2_tie_days']}); median PM2.5 difference "
            f"{pr['median_pm_diff_pts']:+} points of an always-open dose; median requests {pr['median_request_ratio']}× the alarm's.",
            f"Khidki Pareto-dominates the alarm (better or equal on both PM and CO₂) on "
            f"{r['khidki_pareto_dominates_alarm_days']} of {r['days']} days; the alarm dominates Khidki on "
            f"{r['alarm_pareto_dominates_khidki_days']}.",
            "",
        ]
    lines += [
        "## What this does and doesn't show",
        "",
        "- **Khidki's win is CO₂ and attention, not smog.** Against a CO₂ alarm, Khidki cuts the time a class spends",
        "  above 1,500 ppm by roughly three quarters and asks the teacher about a quarter as often, for a few points more",
        "  PM2.5. Turning up the PM weight moves Khidki along its curve until it matches the alarm on both PM and CO₂,",
        "  still with about a third of the requests and much less cold air. It never clearly dominates the alarm on PM",
        "  and CO₂ together.",
        "- **Why the PM lever is small without a purifier.** Forty-odd children need about 3.3 air changes an hour to stay",
        "  under 1,500 ppm, and at that ventilation indoor PM is already ~94% of a fully open room. Timing helps a",
        "  little (close during spikes, purge in recess); a purifier with shut windows is the big lever, and Khidki",
        "  coordinates the two.",
        "- **CAMS reads Delhi low.** The replay days are uncorrected CAMS model values (median 24-hour PM2.5 91 µg/m³), so",
        "  absolute doses are understated; the comparisons are relative.",
        "- **Not a field trial.** The classroom, sensors and teacher are simulated. Real classrooms will differ.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    summary, rows = load()
    chart(summary)
    (ROOT / "docs" / "benchmark.md").write_text(markdown(summary, rows))
    pub = {
        **summary,
        "paired": {room: paired(rows, room, "KHIDKI", "CO2_ALARM") for room in summary["rooms"]},
    }
    (ROOT / "web" / "public" / "benchmark.json").write_text(json.dumps(pub, indent=1))
    print(
        "Wrote docs/benchmark.md, docs/benchmark-pareto.png, bench/results/pareto.png, web/public/benchmark.json"
    )


if __name__ == "__main__":
    main()
