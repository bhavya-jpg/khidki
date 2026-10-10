import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell, Tag } from "../components/Bits";
import { lerp, lineAt, prog, rise } from "../lib";
import { C } from "../theme";

const ID = "s8_results" as const;
// docs/benchmark.md: 48 East Delhi school days (Oct to Dec 2025), class of 44, no purifier, same teacher behaviour
const R = { alarmMin: 65, khidkiMin: 17, alarmReq: 15, khidkiReq: 4, alarmPm: 89, khidkiPm: 93, better: 44, days: 48 };
const ALARM = "#CF7A33", KHIDKI = "#4896CE"; // the chart palette's dark-surface slots 2 and 1

const Bar: React.FC<{ label: string; value: number; max: number; color: string; frame: number; at: number; suffix?: string }> = ({ label, value, max, color, frame, at, suffix = "" }) => {
  const g = prog(frame, at, 26);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 14 }}>
      <div style={{ width: 190, fontSize: 32, fontWeight: 600, color: C.chalkSoft }}>{label}</div>
      <div style={{ width: (value / max) * 430 * g + 6, height: 54, borderRadius: 10, background: color }} />
      <div style={{ fontSize: 60, fontWeight: 800, lineHeight: 1, fontVariantNumeric: "tabular-nums", opacity: g }}>
        {Math.round(lerp(0, value, g))}{suffix}
      </div>
    </div>
  );
};

/** The benchmark, with its limits said out loud. */
export const S8Results: React.FC = () => {
  const frame = useCurrentFrame();
  const l2 = lineAt(ID, 1), l2e = lineAt(ID, 1, "end"), l3 = lineAt(ID, 2);
  const span = l2e - l2;
  return (
    <Shell dark>
      <Audio src={staticFile("vo/s8_results.wav")} />
      <Tag dark>Simulation with real outdoor air. Not a field trial.</Tag>
      <div style={{ position: "absolute", left: 110, top: 104, ...rise(frame, 0) }}>
        <div style={{ fontSize: 118, fontWeight: 800, lineHeight: 1.05 }}>48 real Delhi school days</div>
        <div style={{ marginTop: 8, fontSize: 40, color: C.chalkSoft }}>October to December 2025, a class of 44, against a CO₂ alarm</div>
      </div>
      <div style={{ position: "absolute", left: 110, top: 372, width: 820, ...rise(frame, l2 + span * 0.2, 16) }}>
        <div style={{ fontSize: 40, fontWeight: 700 }}>Stuffy minutes a day <span style={{ fontWeight: 400, color: C.chalkSoft }}>(above 1,500 ppm)</span></div>
        <Bar label="CO₂ alarm" value={R.alarmMin} max={65} color={ALARM} frame={frame} at={l2 + span * 0.24} />
        <Bar label="Khidki" value={R.khidkiMin} max={65} color={KHIDKI} frame={frame} at={l2 + span * 0.44} />
        <div style={{ marginTop: 14, fontSize: 30, color: C.chalkSoft, ...rise(frame, l2 + span * 0.55, 12, 16) }}>Better on {R.better} of {R.days} days</div>
      </div>
      <div style={{ position: "absolute", left: 1000, top: 372, width: 820, ...rise(frame, l2 + span * 0.62, 16) }}>
        <div style={{ fontSize: 40, fontWeight: 700 }}>Requests to the teacher a day</div>
        <Bar label="CO₂ alarm" value={R.alarmReq} max={15} color={ALARM} frame={frame} at={l2 + span * 0.66} />
        <Bar label="Khidki" value={R.khidkiReq} max={15} color={KHIDKI} frame={frame} at={l2 + span * 0.8} />
      </div>
      <div style={{ position: "absolute", left: 110, top: 720, width: 1700, padding: "22px 32px", borderRadius: 22, border: "2px solid rgba(238,240,230,0.3)", display: "flex", alignItems: "center", gap: 34, ...rise(frame, l3 - 4, 16, 30) }}>
        <div style={{ fontSize: 34, fontWeight: 700, flex: "0 0 520px", lineHeight: 1.25 }}>The cost, said plainly: PM2.5 dose, as % of an always-open room</div>
        <div style={{ fontSize: 34, color: C.chalkSoft }}>CO₂ alarm <b style={{ fontSize: 54, color: C.chalk }}>{R.alarmPm}%</b></div>
        <div style={{ fontSize: 34, color: C.chalkSoft }}>Khidki <b style={{ fontSize: 54, color: C.chalk }}>{R.khidkiPm}%</b></div>
        <div style={{ fontSize: 28, color: C.chalkSoft, lineHeight: 1.3 }}>Without a purifier, timing alone cannot cut smog.</div>
      </div>
      <Caption scene={ID} dark />
    </Shell>
  );
};
