// Khidki's design tokens (docs/SPEC.md §14.3), reused so the video and the product look like one thing.
import { loadFont as loadDevanagari } from "@remotion/google-fonts/AnekDevanagari";
import { loadFont as loadLatin } from "@remotion/google-fonts/AnekLatin";

const latin = loadLatin("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] });
const devanagari = loadDevanagari("normal", { weights: ["500", "700", "800"], subsets: ["devanagari"] });

export const FONT = `${latin.fontFamily}, ${devanagari.fontFamily}, system-ui, sans-serif`;
export const FONT_HI = `${devanagari.fontFamily}, ${latin.fontFamily}, system-ui, sans-serif`;

export const C = {
  chalk: "#EEF0E6",
  raised: "#F7F8F2",
  blackboard: "#1F3A30",
  board2: "#27463A",
  haze: "#B7A27E",
  breath: "#1C7DC0",
  breathInk: "#15669E",
  haldi: "#D99A1E",
  ink2: "#3F564C",
  ink3: "#5A6C63",
  rule: "#C9CFC2",
  alarm: "#C2661A", // chart slot 2: the CO₂ alarm baseline
  chalkSoft: "rgba(238, 240, 230, 0.78)",
} as const;

// window states, least to most open: the same four blues as the product's plan ribbon
export const OPEN_COLOR = { closed: "#C9CFC2", cracked: "#A9C7DE", open_one: "#6FA6D4", open_both: "#1C7DC0" } as const;
