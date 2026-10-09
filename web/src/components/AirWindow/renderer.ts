import type { WindowState } from "../../types";
import { DRIFT_ACH, PANE_ANGLES, breathAlpha, particleCount } from "./encoding";

export interface AirState {
  outdoorPm: number;
  indoorPm: number | null;
  co2: number;
  window: WindowState;
  purifier: boolean;
  pmPerParticle: number;
  framePaint: string;
}

interface Dot {
  x: number; // 0..1 across the glass
  y: number; // 0..1 down the glass
  vx: number;
  vy: number;
  r: number;
}

interface Palette {
  haze: string;
  breath: string;
  haldi: string;
  chalk: string;
  ink: string;
  frame: string;
  surface: string;
}

function readPalette(el: Element, framePaint: string): Palette {
  const cs = getComputedStyle(el);
  const v = (name: string, fallback: string) => cs.getPropertyValue(name).trim() || fallback;
  const paint: Record<string, string> = {
    green: v("--window-paint-green", "#1F3A30"),
    blue: v("--window-paint-blue", "#15669E"),
  };
  return {
    haze: v("--haze", "#B7A27E"),
    breath: v("--breath", "#1C7DC0"),
    haldi: v("--haldi", "#D99A1E"),
    chalk: "#EEF0E6",
    ink: v("--blackboard", "#1F3A30"), // the scene looks the same in both themes
    frame: paint[framePaint] ?? paint.green,
    surface: v("--surface", "#EEF0E6"),
  };
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgba(hex: string, a: number): string {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}

/** Linear mix of two hex colours, as hex. */
function mix(a: string, b: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(a);
  const [r2, g2, b2] = hexToRgb(b);
  const m = (x: number, y: number) => Math.round(x + (y - x) * t).toString(16).padStart(2, "0");
  return `#${m(r1, r2)}${m(g1, g2)}${m(b1, b2)}`;
}

/** Seeded so a reduced-motion still frame looks the same every time for the same data. */
function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return ((s >>> 0) % 100000) / 100000;
  };
}

export class AirWindowRenderer {
  private ctx: CanvasRenderingContext2D;
  private w = 0;
  private h = 0;
  private outside: Dot[] = [];
  private inside: Dot[] = [];
  private angles: [number, number] = [0, 0];
  private target: AirState;
  private palette: Palette;
  private raf = 0;
  private lastFrame = 0;
  private lastChange = 0;
  private haze = 0;
  private rand = rng(7);
  readonly fpsCap: number;
  readonly freezeAfterMs: number;
  reducedMotion = false;
  onSlow?: () => void;
  private frameTimes: number[] = [];

  constructor(private canvas: HTMLCanvasElement, state: AirState, opts: { fpsCap: number; freezeAfterMs: number }) {
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas 2D not available");
    this.ctx = ctx;
    this.target = state;
    this.palette = readPalette(canvas, state.framePaint);
    this.fpsCap = opts.fpsCap;
    this.freezeAfterMs = opts.freezeAfterMs;
    this.angles = [...PANE_ANGLES[state.window]] as [number, number];
    this.haze = breathAlpha(state.co2);
    this.syncDots(true);
  }

  resize(cssW: number, cssH: number) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.w = cssW;
    this.h = cssH;
    this.canvas.width = Math.round(cssW * dpr);
    this.canvas.height = Math.round(cssH * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.kick();
  }

  update(state: AirState) {
    const changed =
      state.window !== this.target.window ||
      Math.abs(state.outdoorPm - this.target.outdoorPm) > 0.5 ||
      Math.abs((state.indoorPm ?? 0) - (this.target.indoorPm ?? 0)) > 0.5 ||
      Math.abs(state.co2 - this.target.co2) > 5 ||
      state.pmPerParticle !== this.target.pmPerParticle ||
      state.framePaint !== this.target.framePaint;
    this.target = state;
    this.palette = readPalette(this.canvas, state.framePaint);
    if (changed) {
      this.syncDots(false);
      this.kick();
    }
  }

  refreshPalette() {
    this.palette = readPalette(this.canvas, this.target.framePaint);
    this.kick();
  }

  /** Match dot counts to the data exactly (the honesty rule), keeping existing dots where possible. */
  private syncDots(initial: boolean) {
    const nOut = particleCount(this.target.outdoorPm, this.target.pmPerParticle);
    const nIn = particleCount(this.target.indoorPm ?? 0, this.target.pmPerParticle);
    const make = (r: number): Dot => ({
      x: this.rand(),
      y: this.rand(),
      vx: (this.rand() - 0.5) * 0.02,
      vy: (this.rand() - 0.5) * 0.02,
      r,
    });
    while (this.outside.length < nOut) this.outside.push(make(1.4));
    this.outside.length = nOut;
    while (this.inside.length < nIn) {
      const d = make(2.2);
      if (!initial && this.target.window !== "closed") this.spawnAtOpening(d);
      this.inside.push(d);
    }
    this.inside.length = nIn;
  }

  private spawnAtOpening(d: Dot) {
    const both = this.target.window === "open_both";
    const side = both && this.rand() < 0.5 ? 1 : 0; // 0: road side (left), 1: corridor side (right)
    d.x = side === 0 ? this.rand() * 0.12 : 0.88 + this.rand() * 0.12;
    d.y = 0.1 + this.rand() * 0.8;
    d.vx = (side === 0 ? 1 : -1) * (0.05 + this.rand() * 0.05);
  }

  private kick() {
    this.lastChange = performance.now();
    if (!this.raf) this.raf = requestAnimationFrame(this.loop);
  }

  start() {
    this.kick();
  }

  stop() {
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  private loop = (t: number) => {
    this.raf = 0;
    const minGap = 1000 / this.fpsCap;
    const dt = this.lastFrame ? Math.min(0.1, (t - this.lastFrame) / 1000) : 0;
    if (!this.lastFrame || t - this.lastFrame >= minGap - 1) {
      const t0 = performance.now();
      this.step(this.reducedMotion ? 10 : dt);
      this.draw();
      this.lastFrame = t;
      this.trackSpeed(performance.now() - t0);
    }
    const idle = t - this.lastChange > this.freezeAfterMs;
    const settling = !this.settled();
    if (!this.reducedMotion && (!idle || settling)) this.raf = requestAnimationFrame(this.loop);
    else if (this.reducedMotion && settling) this.raf = requestAnimationFrame(this.loop);
  };

  private trackSpeed(ms: number) {
    this.frameTimes.push(ms);
    if (this.frameTimes.length >= 60) {
      const avg = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
      this.frameTimes = [];
      if (avg > 20) this.onSlow?.();
    }
  }

  private settled() {
    const [a, b] = PANE_ANGLES[this.target.window];
    return Math.abs(this.angles[0] - a) < 0.5 && Math.abs(this.angles[1] - b) < 0.5;
  }

  private step(dt: number) {
    // Panes ease toward their target over ~750 ms.
    const [ta, tb] = PANE_ANGLES[this.target.window];
    const k = this.reducedMotion ? 1 : 1 - Math.exp(-dt / 0.18);
    this.angles = [this.angles[0] + (ta - this.angles[0]) * k, this.angles[1] + (tb - this.angles[1]) * k];
    this.haze += (breathAlpha(this.target.co2) - this.haze) * (this.reducedMotion ? 1 : 1 - Math.exp(-dt / 0.6));
    if (this.reducedMotion) return;
    const wind = 0.015;
    for (const d of this.outside) {
      d.x += (d.vx + wind) * dt;
      d.y += d.vy * dt;
      if (d.x > 1) d.x -= 1;
      if (d.y < 0 || d.y > 1) d.vy = -d.vy;
    }
    const ach = DRIFT_ACH[this.target.window];
    const speed = 0.25 + ach * 0.06;
    for (const d of this.inside) {
      d.vx += (this.rand() - 0.5) * 0.05 * dt;
      d.vy += (this.rand() - 0.5) * 0.05 * dt;
      d.vx *= 0.995;
      d.vy *= 0.995;
      d.x += d.vx * speed * dt;
      d.y += d.vy * speed * dt;
      if (d.x < 0 || d.x > 1 || d.y < 0 || d.y > 1) {
        if (this.target.window !== "closed" && this.rand() < Math.min(1, ach / 8)) this.spawnAtOpening(d);
        else {
          d.x = Math.min(1, Math.max(0, d.x));
          d.y = Math.min(1, Math.max(0, d.y));
          d.vx = -d.vx;
          d.vy = -d.vy;
        }
      }
    }
  }

  private draw() {
    const { ctx, w, h } = this;
    if (!w || !h) return;
    const p = this.palette;
    ctx.clearRect(0, 0, w, h);
    const fw = Math.max(6, Math.min(w, h) * 0.04); // frame width
    const gx = fw, gy = fw, gw = w - 2 * fw, gh = h - 2 * fw; // glass area

    // Outside: sky that turns to smog with outdoor PM.
    const smog = Math.min(1, this.target.outdoorPm / 250);
    const sky = ctx.createLinearGradient(0, gy, 0, gy + gh);
    sky.addColorStop(0, mix(mix(p.breath, p.chalk, 0.55), p.haze, smog));
    sky.addColorStop(1, mix(mix(p.breath, p.chalk, 0.75), p.haze, Math.min(1, smog + 0.15)));
    ctx.fillStyle = sky;
    ctx.fillRect(gx, gy, gw, gh);

    ctx.fillStyle = rgba(mix(p.haze, p.ink, 0.25), 0.8);
    for (const d of this.outside) {
      ctx.beginPath();
      ctx.arc(gx + d.x * gw, gy + d.y * gh, d.r, 0, Math.PI * 2);
      ctx.fill();
    }

    // Glass sashes: two halves, hinged at the outer edges, swinging outward.
    const half = gw / 2;
    this.drawSash(gx, gy, half, gh, this.angles[0], "left", fw);
    this.drawSash(gx + half, gy, half, gh, this.angles[1], "right", fw);

    // Inside air: dots in front of the glass, plus the warm breath haze for CO₂.
    ctx.fillStyle = mix(p.haze, p.ink, 0.45);
    for (const d of this.inside) {
      ctx.beginPath();
      ctx.arc(gx + d.x * gw, gy + d.y * gh, d.r, 0, Math.PI * 2);
      ctx.fill();
    }
    if (this.haze > 0.01) {
      const g = ctx.createRadialGradient(gx + gw / 2, gy + gh * 1.05, gh * 0.1, gx + gw / 2, gy + gh * 0.9, gh * 1.1);
      g.addColorStop(0, rgba(p.haldi, 0.55 * this.haze));
      g.addColorStop(1, rgba(p.haldi, 0));
      ctx.fillStyle = g;
      ctx.fillRect(gx, gy, gw, gh);
    }

    // Frame on top.
    ctx.strokeStyle = p.frame;
    ctx.lineWidth = fw;
    ctx.strokeRect(fw / 2, fw / 2, w - fw, h - fw);
  }

  private drawSash(x: number, y: number, w: number, h: number, angleDeg: number, hinge: "left" | "right", fw: number) {
    const { ctx } = this;
    const p = this.palette;
    const a = (angleDeg * Math.PI) / 180;
    const proj = w * Math.cos(a);
    const shrink = h * 0.12 * Math.sin(a);
    const hx = hinge === "left" ? x : x + w;
    const fx = hinge === "left" ? x + proj : x + w - proj;
    ctx.beginPath();
    ctx.moveTo(hx, y);
    ctx.lineTo(fx, y + shrink / 2);
    ctx.lineTo(fx, y + h - shrink / 2);
    ctx.lineTo(hx, y + h);
    ctx.closePath();
    ctx.fillStyle = rgba(p.chalk, 0.16 + 0.1 * Math.sin(a));
    ctx.fill();
    ctx.strokeStyle = p.frame;
    ctx.lineWidth = Math.max(2, fw * 0.45);
    ctx.stroke();
    // glazing bar across the middle
    ctx.beginPath();
    ctx.moveTo(hx, y + h / 2);
    ctx.lineTo(fx, y + h / 2);
    ctx.lineWidth = Math.max(1.5, fw * 0.3);
    ctx.stroke();
    // a faint reflection on closed glass
    if (angleDeg < 5) {
      ctx.beginPath();
      ctx.moveTo(x + w * 0.2, y + h * 0.15);
      ctx.lineTo(x + w * 0.35, y + h * 0.05);
      ctx.strokeStyle = rgba(p.chalk, 0.5);
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }
}
