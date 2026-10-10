// Capture real footage of Khidki running in local mode (simulated classroom, real outdoor air).
// Screenshots at ~12 fps are stitched with their real timestamps, so the clip is crisp and true to time.
// Usage: node scripts/capture.mjs   (local mode must be running: python tasks.py local partial_open)
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
const require = createRequire(new URL("../../web/", import.meta.url));
const { chromium } = require("playwright");

const WEB = "http://localhost:5173", API = "http://localhost:8000";
const ROOT = path.resolve(new URL("..", import.meta.url).pathname);
const FOOT = `${ROOT}/public/footage`, DATA = `${ROOT}/src/data`, TMP = `${ROOT}/out/frames`;
const j = async (m, p, b) => {
  for (let attempt = 0; ; attempt++) {
    try {
      return await (await fetch(API + p, { method: m, headers: { "content-type": "application/json" }, body: b ? JSON.stringify(b) : undefined })).json();
    } catch (e) {
      if (attempt >= 5) throw e; // the local server resets a connection now and then under load
      await new Promise((r) => setTimeout(r, 300));
    }
  }
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => j("GET", "/v1/rooms/6B/now");
const waitFor = async (pred, ms, label) => { const t0 = Date.now(); for (;;) { const n = await now(); if (pred(n)) return n; if (Date.now() - t0 > ms) throw new Error("timeout: " + label + " at " + n.clock.time + " " + n.card.kind + "/" + n.card.status); await sleep(200); } };

async function addCursor(page) {
  await page.evaluate(() => {
    const c = document.createElement("div");
    c.id = "__cursor";
    c.style.cssText = "position:fixed;left:0;top:0;width:26px;height:26px;border-radius:50%;background:rgba(31,58,48,.28);border:2.5px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,.35);z-index:99999;pointer-events:none;translate:-50% -50%;transition:scale 120ms";
    document.body.appendChild(c);
  });
}
const cursorTo = (page, x, y) => page.evaluate(([x, y]) => { const c = document.getElementById("__cursor"); c.style.left = x + "px"; c.style.top = y + "px"; }, [x, y]);
const cursorPress = (page, down) => page.evaluate((d) => { document.getElementById("__cursor").style.scale = d ? "0.72" : "1"; }, down);

async function record(page, name, steps) {
  const dir = `${TMP}/${name}`;
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const stamps = [];
  let stop = false, i = 0;
  const loop = (async () => { while (!stop) { const f = `${dir}/${String(i).padStart(5, "0")}.jpg`; await page.screenshot({ path: f, type: "jpeg", quality: 94 }); stamps.push(Date.now()); i++; await sleep(25); } })();
  const marks = {};
  const t0 = Date.now();
  await steps((label) => { marks[label] = (Date.now() - t0) / 1000; });
  stop = true;
  await loop;
  // ffconcat with real per-frame durations
  let list = "ffconcat version 1.0\n";
  for (let k = 0; k < stamps.length; k++) {
    const d = k + 1 < stamps.length ? (stamps[k + 1] - stamps[k]) / 1000 : 0.08;
    list += `file '${dir}/${String(k).padStart(5, "0")}.jpg'\nduration ${d.toFixed(4)}\n`;
  }
  fs.writeFileSync(`${dir}/list.txt`, list);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", `${dir}/list.txt`, "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-movflags", "+faststart", `${FOOT}/${name}.mp4`]);
  const dur = (stamps[stamps.length - 1] - stamps[0]) / 1000;
  console.log(name, "frames", stamps.length, "seconds", dur.toFixed(1), "fps", (stamps.length / dur).toFixed(1), "marks", JSON.stringify(marks));
  return { seconds: dur, marks };
}

async function tapPrimary(page, mark) {
  const btn = page.locator(".btn--primary").first();
  const box = await btn.boundingBox();
  const tx = box.x + box.width * 0.55, ty = box.y + box.height * 0.5;
  for (let s = 0; s <= 14; s++) { const k = s / 14, e = 1 - (1 - k) ** 3; await cursorTo(page, 980 + (tx - 980) * e, 760 + (ty - 760) * e); await sleep(45); }
  await sleep(250);
  await cursorPress(page, true); mark("tap"); await btn.click(); await sleep(140); await cursorPress(page, false);
}

fs.mkdirSync(FOOT, { recursive: true }); fs.mkdirSync(DATA, { recursive: true });
const meta = { captured: new Date().toISOString(), note: "Local mode: simulated classroom, real outdoor air (CAMS replay of 2025-11-18).", clips: {} };
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, colorScheme: "light" });
const page = await ctx.newPage();

// ── clip 1: instruction → tap → verified from the CO₂ curve ────────────────────────────────────────
await j("POST", "/v1/sim/control", { action: "scenario", scenario: "partial_open", speed: 40 });
await page.goto(WEB + "/teacher/6B", { waitUntil: "load" });
await waitFor((n) => n.card.kind === "action" && n.card.status === "issued", 120000, "first instruction");
await j("POST", "/v1/sim/control", { action: "speed", speed: 12 });
await sleep(1500);
await addCursor(page); await cursorTo(page, 980, 760);
let first;
meta.clips.instruction = await record(page, "instruction", async (mark) => {
  first = await now();
  mark("instruction");
  await sleep(3200);
  await tapPrimary(page, mark);
  const n = await waitFor((n) => n.card.kind === "keep" && n.last_outcome, 90000, "verification");
  mark("verified"); meta.firstOutcome = n.last_outcome.status;
  await sleep(3200);
});
meta.first = { text: first.card.text, reason: first.card.reason, time: first.clock.time, co2: first.indoor.co2 };
const afterFirst = await now();
meta.afterFirst = { time: afterFirst.clock.time, co2: afterFirst.indoor.co2, inferred: afterFirst.window.inferred, implied_lam: afterFirst.window.implied_lam, outcome: afterFirst.last_outcome };

// keep following instructions (tapping) at speed until "open both sides" is asked
await j("POST", "/v1/sim/control", { action: "speed", speed: 40 });
let both = null;
for (const t0 = Date.now(); Date.now() - t0 < 200000;) {
  const n = await now();
  if (n.card.kind === "action" && n.card.status === "issued") {
    if (n.card.action.window === "open_both") { both = n; break; }
    await j("POST", `/v1/nudges/${n.card.nudge_id}/ack`, { result: "done" });
  }
  await sleep(250);
}
// ── clip 2: "open both sides", only one side really opens (the simulator's scripted mistake) ──────────
if (both) {
  await j("POST", "/v1/sim/control", { action: "speed", speed: 12 });
  await sleep(1200);
  await cursorTo(page, 980, 760);
  let outcome = "none";
  meta.clips.followup = await record(page, "followup", async (mark) => {
    mark("instruction");
    await sleep(2200);
    await tapPrimary(page, mark);
    const n = await waitFor((n) => (n.card.kind === "action" && n.card.status === "follow_up") || (n.card.kind === "keep" && n.last_outcome?.nudge_id === both.card.nudge_id), 90000, "partial verdict");
    if (n.card.kind === "action") {
      outcome = "follow_up:" + n.card.follow_up; mark("follow_up");
      await sleep(3600);
      await tapPrimary(page, (l) => mark("tap2"));
      const m = await waitFor((n) => n.card.kind === "keep" && n.last_outcome?.nudge_id === both.card.nudge_id, 90000, "second verification");
      mark("verified"); outcome += " then " + m.last_outcome.status;
      await sleep(3000);
    } else { outcome = "no follow-up: " + n.last_outcome.status; await sleep(1500); }
  });
  meta.followupOutcome = outcome;
  console.log("follow-up clip outcome:", outcome);
}
// ── data behind the graphics: the real plan, decisions and CO₂ series from this run ───────────────────
const end = await now();
const plan = await j("GET", "/v1/rooms/6B/plan");
const today = await j("GET", "/v1/schools/dsv/today");
fs.writeFileSync(`${DATA}/run.json`, JSON.stringify({
  date: end.clock.date, series: end.series, day_steps: plan.day_steps, timetable: plan.timetable,
  decisions: today.decisions, policies: today.policies, city_aqi: today.city_aqi, grap: today.grap, outdoor: end.outdoor, requests: end.requests,
}, null, 1));
// ── stills: principal page and printable timetable ────────────────────────────────────────────────────
await j("POST", "/v1/sim/control", { action: "pause" });
const still = await (await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })).newPage();
await still.goto(WEB + "/school/dsv", { waitUntil: "load" }); await still.waitForTimeout(2500);
await still.screenshot({ path: `${FOOT}/principal.png` });
await still.goto(WEB + "/print/6B", { waitUntil: "load" }); await still.waitForTimeout(2000);
await still.screenshot({ path: `${FOOT}/print.png` });
await j("POST", "/v1/sim/control", { action: "resume" });
fs.writeFileSync(`${DATA}/capture.json`, JSON.stringify(meta, null, 1));
await browser.close();
console.log("done", JSON.stringify(meta.clips));
