import { Easing, interpolate } from "remotion";
import voJson from "./data/vo.json";

export const EASE = Easing.bezier(0.2, 0.7, 0.2, 1);

/** 0 → 1 between `start` and `start + dur` frames, eased and clamped. */
export const prog = (frame: number, start: number, dur = 18): number =>
  interpolate(frame, [start, start + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE });

/** Fade up into place. */
export const rise = (frame: number, start: number, dur = 18, dist = 36) => ({
  opacity: prog(frame, start, dur),
  translate: `0px ${(1 - prog(frame, start, dur)) * dist}px`,
});

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const num = (n: number) => Math.round(n).toLocaleString("en-IN");

export type SceneId = keyof typeof voJson;
type Line = { text: string; start: number; end: number };
export const VO = voJson as Record<SceneId, { seconds: number; lines: Line[] }>;

export const SCENES: SceneId[] = ["s1_question", "s2_dilemma", "s3_khidki", "s4_plan", "s5_instruction", "s6_verify", "s7_aws", "s8_results", "s9_close"];
export const FPS = 30;
export const TRANSITION = 12; // frames of cross-fade between scenes
const HOLD = 0.55; // seconds a scene stays after its last word

export const sceneFrames = (id: SceneId) => Math.ceil((VO[id].seconds + HOLD) * FPS);
export const totalFrames = () => SCENES.reduce((s, id) => s + sceneFrames(id), 0) - TRANSITION * (SCENES.length - 1);
/** Frame at which narration line `i` of a scene starts (or ends). */
export const lineAt = (id: SceneId, i: number, edge: "start" | "end" = "start") => Math.round(VO[id].lines[Math.min(i, VO[id].lines.length - 1)][edge] * FPS);
