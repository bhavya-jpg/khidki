import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell, Tag } from "../components/Bits";
import run from "../data/run.json";
import { lineAt, prog, rise } from "../lib";
import { C, OPEN_COLOR } from "../theme";

const ID = "s4_decide" as const;
type StepRow = { t_min: number; window: keyof typeof OPEN_COLOR; predicted_co2: number };
const steps = run.day_steps as StepRow[];
// The model's air changes per hour for each window setting (core/khidki_core/schemas.py, default room).
const AIR: [string, number, keyof typeof OPEN_COLOR][] = [["Shut", 0.7, "closed"], ["A little open", 2.5, "cracked"], ["One side open", 6, "open_one"], ["Both sides open", 10, "open_both"]];

/**
 * How Khidki decides when: a physics model of the room, the outdoor forecast and the timetable. No hardware
 * is involved in this part. The curve is the model's own forecast of CO₂ for the plan it kept in this run.
 */
export const S4Decide: React.FC = () => {
  const frame = useCurrentFrame();
  const twin = lineAt(ID, 1);
  const twinSpan = lineAt(ID, 1, "end") - twin;
  const plan = lineAt(ID, 2);
  const planSpan = lineAt(ID, 2, "end") - plan;
  const W = 800, H = 250, L = 76, R = 14, T = 14, B = 8;
  const x = (m: number) => L + ((m - 450) / 360) * (W - L - R);
  const y = (v: number) => T + (1 - (v - 400) / 1300) * (H - T - B);
  const d = steps.map((s, i) => `${i ? "L" : "M"}${x(s.t_min).toFixed(1)} ${y(s.predicted_co2).toFixed(1)}`).join(" ");
  const draw = prog(frame, plan + planSpan * 0.3, planSpan * 0.55);
  return (
    <Shell>
      <Audio src={staticFile("vo/s4_decide.wav")} />
      <Tag>The forecast and plan are from this run</Tag>
      <div style={{ position: "absolute", left: 110, top: 84, ...rise(frame, 0) }}>
        <div style={{ fontSize: 100, fontWeight: 800, lineHeight: 1.05 }}>How does it know when?</div>
        <div style={{ marginTop: 8, fontSize: 48, fontWeight: 700, color: C.breathInk, ...rise(frame, 16) }}>Deciding needs no hardware at all.</div>
      </div>
      <div style={{ position: "absolute", left: 110, top: 318, width: 790, height: 506, padding: "28px 34px", borderRadius: 28, background: C.raised, boxShadow: "0 40px 80px -46px rgba(31,58,48,0.5)", boxSizing: "border-box", ...rise(frame, twin - 6, 18, 44) }}>
        <div style={{ fontSize: 42, fontWeight: 800 }}>A physics twin of the classroom</div>
        <div style={{ marginTop: 18, display: "flex", alignItems: "baseline", gap: 16, ...rise(frame, twin + twinSpan * 0.25, 14, 20) }}>
          <span style={{ fontSize: 30, color: C.ink2, width: 190, lineHeight: 1.2 }}>44 children add</span>
          <span style={{ fontSize: 96, fontWeight: 800, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>+3,450</span>
          <span style={{ fontSize: 30, color: C.ink2 }}>ppm CO₂ an hour</span>
        </div>
        <div style={{ marginTop: 22, fontSize: 30, fontWeight: 700, ...rise(frame, twin + twinSpan * 0.55, 14, 20) }}>Air changes an hour, by window setting</div>
        {AIR.map(([label, v, key], i) => {
          const g = prog(frame, twin + twinSpan * 0.6 + i * 5, 16);
          return (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 9, opacity: g }}>
              <span style={{ width: 210, fontSize: 28, color: C.ink2 }}>{label}</span>
              <span style={{ width: (v / 10) * 360 * g + 6, height: 30, borderRadius: 7, background: OPEN_COLOR[key] }} />
              <span style={{ fontSize: 32, fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>{v}</span>
            </div>
          );
        })}
        <div style={{ marginTop: 14, fontSize: 28, color: C.ink2, ...rise(frame, twin + twinSpan * 0.85, 12, 14) }}>More air out also means more smog in.</div>
      </div>
      <div style={{ position: "absolute", left: 930, top: 318, width: 880, height: 506, padding: "28px 34px", borderRadius: 28, background: C.raised, boxShadow: "0 40px 80px -46px rgba(31,58,48,0.5)", boxSizing: "border-box", ...rise(frame, plan - 6, 18, 44) }}>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span style={{ fontSize: 42, fontWeight: 800, marginRight: 6 }}>06:00</span>
          {["Outdoor air forecast", "School timetable"].map((t, i) => (
            <span key={t} style={{ padding: "8px 20px", borderRadius: 999, border: `2px solid ${C.rule}`, fontSize: 28, fontWeight: 600, ...rise(frame, plan + 8 + i * 14, 12, 16) }}>{t}</span>
          ))}
        </div>
        <div style={{ marginTop: 12, fontSize: 28, color: C.ink2 }}>The plan it kept, and the twin's forecast of CO₂ for it</div>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ marginTop: 6, display: "block" }}>
          {[500, 1000, 1500].map((v) => (
            <g key={v}>
              <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={v === 1500 ? C.ink3 : C.rule} strokeWidth={2} strokeDasharray={v === 1500 ? "8 6" : undefined} />
              <text x={L - 10} y={y(v) + 9} textAnchor="end" fontSize={24} fill={C.ink2}>{v.toLocaleString("en-IN")}</text>
            </g>
          ))}
          <text x={W - R} y={y(1500) - 10} textAnchor="end" fontSize={24} fontWeight={600} fill={C.ink2}>stuffy above 1,500 ppm</text>
          <path d={d} fill="none" stroke={C.blackboard} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
        </svg>
        <div style={{ position: "relative", height: 40, width: W, marginTop: 2 }}>
          {steps.map((s, i) => (
            <div key={s.t_min} style={{ position: "absolute", left: x(s.t_min) + 1, width: x(s.t_min + 5) - x(s.t_min) - 2, top: 0, bottom: 0, borderRadius: 3, background: OPEN_COLOR[s.window], opacity: prog(frame, plan + planSpan * 0.3 + (i / steps.length) * planSpan * 0.55, 6) }} />
          ))}
        </div>
        <div style={{ position: "relative", height: 34, width: W, fontSize: 24, color: C.ink2 }}>
          {[480, 600, 720].map((m) => (
            <span key={m} style={{ position: "absolute", left: x(m) - 40, width: 80, textAlign: "center", top: 4 }}>{String(m / 60).padStart(2, "0")}:00</span>
          ))}
        </div>
        <div style={{ fontSize: 26, color: C.ink2 }}>One stripe = 5 minutes. Bluer = more open.</div>
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
