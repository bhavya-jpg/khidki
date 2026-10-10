import run from "../data/run.json";
import { prog } from "../lib";
import { C, FONT } from "../theme";

const hm = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3));

/**
 * The CO₂ readings from the captured run (Class 6B, simulated sensor), drawn as they happened: a slow fall
 * with one side open, then a faster one once the corridor side opens too. Nothing here is illustrative.
 */
export const Curve: React.FC<{ width: number; height: number; frame: number; from: number; over: number; askedAt: string; bothAt: string }> = ({
  width, height, frame, from, over, askedAt, bothAt,
}) => {
  const pts = run.series.map((s) => ({ m: hm(s.t), v: s.co2 }));
  const m0 = pts[0].m, m1 = pts[pts.length - 1].m;
  const lo = 900, hi = 1400;
  const L = 86, R = 24, T = 26, B = 56;
  const x = (m: number) => L + ((m - m0) / (m1 - m0)) * (width - L - R);
  const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (height - T - B);
  const d = pts.map((p, i) => `${i ? "L" : "M"}${x(p.m).toFixed(1)} ${y(p.v).toFixed(1)}`).join(" ");
  const draw = prog(frame, from, over);
  const asked = hm(askedAt), both = hm(bothAt);
  const at = (m: number) => pts.reduce((best, p) => (Math.abs(p.m - m) < Math.abs(best.m - m) ? p : best), pts[0]);
  const seen = (m: number) => (draw >= (m - m0) / (m1 - m0) ? 1 : 0);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ fontFamily: FONT, overflow: "visible" }}>
      {[1000, 1200, 1400].map((v) => (
        <g key={v}>
          <line x1={L} x2={width - R} y1={y(v)} y2={y(v)} stroke={C.rule} strokeWidth={2} />
          <text x={L - 12} y={y(v) + 9} textAnchor="end" fontSize={24} fill={C.ink2}>{v.toLocaleString("en-IN")}</text>
        </g>
      ))}
      {[m0, asked, m1].map((m, i) => (
        <text key={m} x={x(m)} y={height - 14} textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"} fontSize={24} fill={C.ink2}>
          {`${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`}
        </text>
      ))}
      <path d={d} fill="none" stroke={C.breath} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
      <g opacity={seen(asked)}>
        <line x1={x(asked)} x2={x(asked)} y1={T} y2={height - B} stroke={C.ink3} strokeWidth={2} strokeDasharray="6 6" />
        <circle cx={x(asked)} cy={y(at(asked).v)} r={10} fill={C.blackboard} />
        <text x={x(asked) - 14} y={T + 22} textAnchor="end" fontSize={26} fontWeight={700} fill={C.blackboard}>Asked for both sides</text>
      </g>
      <g opacity={seen(both)}>
        <circle cx={x(both)} cy={y(at(both).v)} r={10} fill={C.breath} />
      </g>
      <text x={x(m0 + (asked - m0) * 0.42)} y={y(1215) - 34} textAnchor="middle" fontSize={26} fontWeight={600} fill={C.ink2} opacity={seen(m0 + (asked - m0) * 0.6)}>
        One side open: slow fall
      </text>
      <text x={width - R} y={y(940) + 46} textAnchor="end" fontSize={26} fontWeight={700} fill={C.breathInk} opacity={seen(m1 - 1)}>
        Both sides: faster
      </text>
    </svg>
  );
};
