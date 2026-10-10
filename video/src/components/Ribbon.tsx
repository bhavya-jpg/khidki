import run from "../data/run.json";
import { prog } from "../lib";
import { C, OPEN_COLOR } from "../theme";

const START = 420, END = 810; // 07:00 to 13:30
const PERIODS: [number, number, string][] = [
  [450, 470, "Assembly"], [470, 505, "1"], [505, 540, "2"], [540, 575, "3"], [575, 610, "4"], [610, 640, "Recess"],
  [640, 675, "5"], [675, 710, "6"], [710, 745, "7"], [745, 780, "8"],
];
type StepRow = { t_min: number; window: keyof typeof OPEN_COLOR };

/** The day's real plan for Class 6B: one stripe per 5 minutes, bluer = more open. Stripes arrive left to right. */
export const Ribbon: React.FC<{ width: number; frame: number; from: number; over: number }> = ({ width, frame, from, over }) => {
  const steps = run.day_steps as StepRow[];
  const x = (m: number) => ((m - START) / (END - START)) * width;
  return (
    <div style={{ width, position: "relative", height: 190 }}>
      {PERIODS.map(([a, b, label]) => (
        <div key={a} style={{ position: "absolute", left: x(a), width: x(b) - x(a), top: 0, height: 38, borderLeft: `2px solid ${C.rule}`, fontSize: 26, fontWeight: 500, color: C.ink2, textAlign: "center", lineHeight: "38px" }}>
          {label}
        </div>
      ))}
      <div style={{ position: "absolute", left: 0, top: 46, width, height: 64, borderRadius: 14, background: "#DDE1D5", overflow: "hidden" }}>
        {steps.map((s, i) => (
          <div
            key={s.t_min}
            style={{
              position: "absolute", left: x(s.t_min) + 1.5, width: x(s.t_min + 5) - x(s.t_min) - 3, top: 0, bottom: 0, borderRadius: 3, background: OPEN_COLOR[s.window],
              opacity: prog(frame, from + (i / steps.length) * over, 8), scale: `1 ${prog(frame, from + (i / steps.length) * over, 10)}`,
            }}
          />
        ))}
      </div>
      {[420, 480, 540, 600, 660, 720, 780].map((m) => (
        <div key={m} style={{ position: "absolute", left: x(m) - 40, width: 80, top: 118, textAlign: "center", fontSize: 26, color: C.ink2, fontVariantNumeric: "tabular-nums" }}>
          {String(Math.floor(m / 60)).padStart(2, "0")}:00
        </div>
      ))}
      <div style={{ position: "absolute", left: 0, top: 158, display: "flex", gap: 34, fontSize: 26, color: C.ink2, alignItems: "center" }}>
        <b style={{ fontWeight: 700, color: C.blackboard }}>One stripe = 5 minutes</b>
        {([["closed", "Shut"], ["open_one", "One side open"], ["open_both", "Both sides open"]] as const).map(([k, label]) => (
          <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
            <i style={{ width: 28, height: 18, borderRadius: 4, background: OPEN_COLOR[k], display: "inline-block" }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
};
