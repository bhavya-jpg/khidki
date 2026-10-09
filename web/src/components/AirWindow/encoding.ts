import { createContext, useContext } from "react";
import type { WindowState } from "../../types";

/**
 * The encoding contract (docs/SPEC.md §14.5). One dot = PM_PER_PARTICLE µg/m³ of PM2.5 in that window,
 * the same for every AirWindow on the page. If the renderer must drop particles for speed, it changes this
 * shared value (and so every legend) together, never one window alone.
 */
export const DEFAULT_PM_PER_PARTICLE = 2;
export const EncodingContext = createContext<{ pmPerParticle: number; setPmPerParticle: (n: number) => void }>({
  pmPerParticle: DEFAULT_PM_PER_PARTICLE,
  setPmPerParticle: () => {},
});
export const useEncoding = () => useContext(EncodingContext);

export function particleCount(pm: number, pmPerParticle: number): number {
  return Math.max(0, Math.round(pm / pmPerParticle));
}

/** Breath haze opacity from CO₂: 0 at 400 ppm, full at 2,400 ppm. Same mapping everywhere. */
export function breathAlpha(co2: number): number {
  return Math.min(1, Math.max(0, (co2 - 400) / 2000));
}

/** Pane angles (degrees) for [road side, corridor side]. Road side opens first. */
export const PANE_ANGLES: Record<WindowState, [number, number]> = {
  closed: [0, 0],
  cracked: [25, 0],
  open_one: [70, 0],
  open_both: [70, 70],
};

/** Typical air changes per hour, used only for how fast the inside dots drift (motion, not density). */
export const DRIFT_ACH: Record<WindowState, number> = { closed: 0.7, cracked: 2.5, open_one: 6, open_both: 10 };

export function describe(
  window: WindowState,
  outdoorPm: number,
  indoorPm: number | null,
  co2: number,
  lang: "hi" | "en",
  rising?: boolean,
): string {
  const w = {
    en: { closed: "Windows closed", cracked: "One window slightly open", open_one: "Road-side windows open", open_both: "Windows open on both sides" },
    hi: { closed: "खिड़कियाँ बंद", cracked: "एक खिड़की थोड़ी खुली", open_one: "सड़क की तरफ़ की खिड़कियाँ खुली", open_both: "दोनों तरफ़ की खिड़कियाँ खुली" },
  }[lang][window];
  const pmIn = indoorPm == null ? "" : lang === "en" ? `, inside ${Math.round(indoorPm)}` : `, अंदर ${Math.round(indoorPm)}`;
  if (lang === "en") {
    return `${w}. Outside PM2.5 ${Math.round(outdoorPm)}${pmIn} µg/m³. CO₂ ${Math.round(co2).toLocaleString("en-IN")} ppm${rising ? " and rising" : ""}.`;
  }
  return `${w}। बाहर PM2.5 ${Math.round(outdoorPm)}${pmIn} µg/m³। CO₂ ${Math.round(co2).toLocaleString("en-IN")} ppm${rising ? ", बढ़ रहा है" : ""}।`;
}
