// Cut the captured clips to the narration, once, with FFmpeg, so the video plays them at normal speed.
// (Speeding clips up inside the renderer dropped frames.) Re-run after the narration or the capture changes.
// Usage: node scripts/edit-footage.mjs
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(new URL("..", import.meta.url).pathname);
const vo = JSON.parse(fs.readFileSync(`${ROOT}/src/data/vo.json`, "utf8"));
const cap = JSON.parse(fs.readFileSync(`${ROOT}/src/data/capture.json`, "utf8"));
const FPS = 30, HOLD = 0.45, TRANSITION = 12;
const lineAt = (id, i, edge = "start") => Math.round(vo[id].lines[i][edge] * FPS);
const sceneFrames = (id) => Math.ceil((vo[id].seconds + HOLD) * FPS);

/** segments: [sourceStart s, sourceEnd s, frames it should last in the video] */
function cut(src, out, segments) {
  const parts = segments.map(([s, e, frames], i) => `[0:v]trim=start=${s.toFixed(3)}:end=${e.toFixed(3)},setpts=(PTS-STARTPTS)*${(frames / FPS / (e - s)).toFixed(5)},fps=${FPS}[v${i}]`);
  const graph = `${parts.join(";")};${segments.map((_, i) => `[v${i}]`).join("")}concat=n=${segments.length}:v=1:a=0,format=yuv420p[out]`;
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", `${ROOT}/public/footage/${src}`, "-filter_complex", graph, "-map", "[out]", "-c:v", "libx264", "-crf", "15", "-preset", "slow", "-movflags", "+faststart", `${ROOT}/public/footage/${out}`]);
  const total = segments.reduce((n, s) => n + s[2], 0);
  console.log(out, segments.map(([s, e, f]) => `${s.toFixed(1)}–${e.toFixed(1)}s in ${f}f (${((e - s) / (f / FPS)).toFixed(2)}×)`).join(" | "), `= ${total} frames`);
  return total;
}

const edits = {};

// Scene 5: the instruction, then the tap lands on "One tap says it's done".
{
  const id = "s5_instruction";
  const tap = cap.clips.instruction.marks.tap;
  const tapAt = lineAt(id, 1) + Math.round(0.35 * FPS);
  const rest = sceneFrames(id) - tapAt + TRANSITION + 6;
  edits.instruction = { tapAt, frames: cut("instruction.mp4", "instruction-edit.mp4", [[0, tap, tapAt], [tap, tap + rest / FPS, rest]]) };
}

// Scene 6: "open both sides" → only one side opens → follow-up → second tap → verified.
{
  const id = "s6_verify";
  const m = cap.clips.followup.marks;
  const T = { start: 3.0, banner: m.follow_up + 1.2, tap2: m.tap2 + 0.5, tick: m.verified + 1.8, end: cap.clips.followup.seconds - 0.1 };
  const a = lineAt(id, 3) - 7, b = lineAt(id, 4) - 3, c = lineAt(id, 4, "end") - 15; // banner, second tap, tick
  const rest = sceneFrames(id) - c + TRANSITION + 6;
  edits.verify = { bannerAt: a, secondTapAt: b, tickAt: c, frames: cut("followup.mp4", "verify-edit.mp4", [[T.start, T.banner, a], [T.banner, T.tap2, b - a], [T.tap2, T.tick, c - b], [T.tick, T.end, rest]]) };
}
fs.writeFileSync(`${ROOT}/src/data/edits.json`, JSON.stringify(edits, null, 1));
console.log(JSON.stringify(edits));
