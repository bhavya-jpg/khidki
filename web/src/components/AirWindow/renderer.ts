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

interface Building {
  x: number;
  w: number;
  h: number;
  tank: boolean;
  tankX: number;
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

  /** Two layers of Delhi rooftops (with water tanks), generated once per window so they don't jump. */
  private skyline: { far: Building[]; near: Building[] } | null = null;

  private buildSkyline() {
    const r = rng(42);
    const make = (n: number, hMin: number, hMax: number): Building[] => {
      const out: Building[] = [];
      let x = -0.02;
      for (let i = 0; i < n && x < 1.02; i++) {
        const w = 0.05 + r() * 0.09;
        out.push({ x, w, h: hMin + r() * (hMax - hMin), tank: r() < 0.45, tankX: 0.2 + r() * 0.5 });
        x += w + r() * 0.015;
      }
      return out;
    };
    this.skyline = { far: make(24, 0.16, 0.34), near: make(18, 0.08, 0.22) };
  }

  private draw() {
    const { ctx, w, h } = this;
    if (!w || !h) return;
    const p = this.palette;
    if (!this.skyline) this.buildSkyline();
    ctx.clearRect(0, 0, w, h);
    const fw = Math.max(8, Math.min(w, h) * 0.05); // frame width
    const sill = fw * 0.9;
    const gx = fw, gy = fw, gw = w - 2 * fw, gh = h - 2 * fw - sill; // glass area
    const smog = Math.min(1, this.target.outdoorPm / 250);

    ctx.save();
    ctx.beginPath();
    ctx.rect(gx, gy, gw, gh);
    ctx.clip();

    // Sky: clear blue turning to smog-beige as outdoor PM rises.
    const sky = ctx.createLinearGradient(0, gy, 0, gy + gh);
    sky.addColorStop(0, mix(mix(p.breath, p.chalk, 0.45), p.haze, smog * 0.95));
    sky.addColorStop(0.65, mix(mix(p.breath, p.chalk, 0.75), p.haze, Math.min(1, smog * 0.9 + 0.1)));
    sky.addColorStop(1, mix(p.chalk, p.haze, Math.min(1, smog + 0.2)));
    ctx.fillStyle = sky;
    ctx.fillRect(gx, gy, gw, gh);

    // A sun that the smog swallows.
    const sx = gx + gw * 0.74, sy = gy + gh * 0.26, sr = Math.min(gw, gh) * 0.07;
    const sun = ctx.createRadialGradient(sx, sy, 0, sx, sy, sr * (3 + smog * 3));
    sun.addColorStop(0, rgba("#FFF4D6", 0.95 - smog * 0.55));
    sun.addColorStop(0.25, rgba("#FFE7A8", 0.55 - smog * 0.35));
    sun.addColorStop(1, rgba("#FFE7A8", 0));
    ctx.fillStyle = sun;
    ctx.fillRect(gx, gy, gw, gh);

    // Skyline: the far layer disappears first as the air thickens.
    const base = gy + gh;
    const drawLayer = (layer: Building[], color: string, alpha: number) => {
      if (alpha <= 0.01) return;
      ctx.fillStyle = rgba(color, alpha);
      for (const b of layer) {
        const bx = gx + b.x * gw, bw = b.w * gw, bh = b.h * gh;
        ctx.fillRect(bx, base - bh, bw, bh);
        if (b.tank) {
          const tw = bw * 0.28, th = bh * 0.16 + 4;
          ctx.fillRect(bx + b.tankX * bw, base - bh - th, tw, th);
        }
      }
    };
    drawLayer(this.skyline!.far, mix(p.ink, p.chalk, 0.55), Math.max(0, 0.55 * Math.pow(1 - smog, 1.6)));
    // Smog veil between the layers.
    const veil = ctx.createLinearGradient(0, gy + gh * 0.35, 0, base);
    veil.addColorStop(0, rgba(p.haze, 0));
    veil.addColorStop(1, rgba(p.haze, 0.25 + smog * 0.45));
    ctx.fillStyle = veil;
    ctx.fillRect(gx, gy, gw, gh);
    drawLayer(this.skyline!.near, mix(p.ink, p.chalk, 0.3), Math.max(0.08, 0.8 * (1 - smog * 0.8)));

    // Outside air: dots behind the glass.
    ctx.fillStyle = rgba(mix(p.haze, p.ink, 0.35), 0.75);
    for (const d of this.outside) {
      ctx.beginPath();
      ctx.arc(gx + d.x * gw, gy + d.y * gh, d.r, 0, Math.PI * 2);
      ctx.fill();
    }

    // Glass sashes, hinged at the outer edges, swinging outward.
    const half = gw / 2;
    this.drawSash(gx, gy, half, gh, this.angles[0], "left", fw);
    this.drawSash(gx + half, gy, half, gh, this.angles[1], "right", fw);

    // Inside air: dots in front of the glass, plus the warm breath haze for CO₂.
    ctx.fillStyle = rgba(mix(p.haze, p.ink, 0.55), 0.9);
    for (const d of this.inside) {
      ctx.beginPath();
      ctx.arc(gx + d.x * gw, gy + d.y * gh, d.r, 0, Math.PI * 2);
      ctx.fill();
    }
    if (this.haze > 0.01) {
      const g = ctx.createRadialGradient(gx + gw / 2, base + gh * 0.1, gh * 0.1, gx + gw / 2, base, gh * 1.15);
      g.addColorStop(0, rgba(p.haldi, 0.6 * this.haze));
      g.addColorStop(0.6, rgba(p.haldi, 0.25 * this.haze));
      g.addColorStop(1, rgba(p.haldi, 0));
      ctx.fillStyle = g;
      ctx.fillRect(gx, gy, gw, gh);
    }
    ctx.restore();

    // Painted frame with a bevel, and a sill.
    ctx.fillStyle = p.frame;
    ctx.fillRect(0, 0, w, fw);
    ctx.fillRect(0, 0, fw, h);
    ctx.fillRect(w - fw, 0, fw, h);
    ctx.fillRect(0, h - fw - sill, w, fw + sill);
    ctx.strokeStyle = rgba("#FFFFFF", 0.22);
    ctx.lineWidth = 1.5;
    ctx.strokeRect(1, 1, w - 2, h - 2);
    ctx.strokeStyle = rgba("#000000", 0.28);
    ctx.strokeRect(gx - 0.75, gy - 0.75, gw + 1.5, gh + 1.5);
    // sill: a ledge catching the light
    ctx.fillStyle = rgba("#FFFFFF", 0.18);
    ctx.fillRect(0, h - sill - fw * 0.55, w, Math.max(2, fw * 0.18));
    ctx.fillStyle = rgba("#000000", 0.18);
    ctx.fillRect(0, h - Math.max(2, fw * 0.25), w, Math.max(2, fw * 0.25));
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
    const glass = ctx.createLinearGradient(Math.min(hx, fx), y, Math.max(hx, fx), y + h);
    glass.addColorStop(0, rgba("#FFFFFF", 0.2 + 0.1 * Math.sin(a)));
    glass.addColorStop(0.5, rgba(p.breath, 0.06));
    glass.addColorStop(1, rgba("#FFFFFF", 0.12));
    ctx.fillStyle = glass;
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
      ctx.strokeStyle = rgba("#FFFFFF", 0.45);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x + w * 0.16, y + h * 0.34);
      ctx.lineTo(x + w * 0.42, y + h * 0.06);
      ctx.stroke();
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x + w * 0.24, y + h * 0.4);
      ctx.lineTo(x + w * 0.52, y + h * 0.1);
      ctx.stroke();
    }
  }
}
