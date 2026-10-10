import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell } from "../components/Bits";
import { lineAt, prog, rise } from "../lib";
import { C, FONT_HI, OPEN_COLOR } from "../theme";

const ID = "s3_khidki" as const;

const Step: React.FC<{ n: string; title: string; frame: number; at: number; children: React.ReactNode }> = ({ n, title, frame, at, children }) => (
  <div style={{ width: 500, padding: "30px 34px 34px", borderRadius: 30, background: "rgba(238,240,230,0.08)", border: "2px solid rgba(238,240,230,0.2)", ...rise(frame, at, 18, 46) }}>
    <div style={{ fontSize: 40, fontWeight: 800, color: "#7FB8E3" }}>{n}</div>
    <div style={{ marginTop: 6, fontSize: 54, fontWeight: 800 }}>{title}</div>
    <div style={{ marginTop: 22, height: 96, display: "flex", alignItems: "center" }}>{children}</div>
  </div>
);

/** The name, and the three things it does. */
export const S3Khidki: React.FC = () => {
  const frame = useCurrentFrame();
  const l2 = lineAt(ID, 1);
  const l2end = lineAt(ID, 1, "end");
  const span = Math.max(l2end - l2, 60);
  const lift = prog(frame, l2 - 14, 26);
  const draw = prog(frame, l2 + span * 0.62, 40);
  return (
    <Shell dark>
      <Audio src={staticFile("vo/s3_khidki.wav")} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 150 - lift * 70, textAlign: "center" }}>
        <div style={{ fontFamily: FONT_HI, fontSize: 250 - lift * 60, fontWeight: 800, lineHeight: 1.2, ...rise(frame, 0, 24, 70) }}>खिड़की</div>
        <div style={{ fontSize: 64, fontWeight: 700, marginTop: -6, ...rise(frame, 10, 20) }}>
          Khidki <span style={{ fontWeight: 400, color: C.chalkSoft }}>is Hindi for window</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 110, right: 110, top: 520, display: "flex", justifyContent: "space-between" }}>
        <Step n="1" title="Plan the day" frame={frame} at={l2 - 4}>
          <div style={{ display: "flex", gap: 5 }}>
            {Array.from({ length: 22 }, (_, i) => (
              <div key={i} style={{ width: 14, height: 52, borderRadius: 4, background: i < 5 ? OPEN_COLOR.closed : i < 11 ? OPEN_COLOR.open_one : OPEN_COLOR.open_both, opacity: prog(frame, l2 + 4 + i * 1.4, 8) }} />
            ))}
          </div>
        </Step>
        <Step n="2" title="Tell the teacher" frame={frame} at={l2 + span * 0.28}>
          <div style={{ padding: "16px 30px", borderRadius: 16, background: C.breathInk, fontSize: 36, fontWeight: 700, fontFamily: FONT_HI }}>खोल दीं ✓</div>
        </Step>
        <Step n="3" title="Check the air" frame={frame} at={l2 + span * 0.56}>
          <svg width={420} height={96} viewBox="0 0 420 96">
            <path d="M4 70 C 70 60, 110 22, 160 16 S 260 60, 416 78" fill="none" stroke="#7FB8E3" strokeWidth={7} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
            <circle cx={160} cy={16} r={11} fill={C.chalk} opacity={prog(frame, l2 + span * 0.62 + 12, 8)} />
          </svg>
        </Step>
      </div>
      <Caption scene={ID} dark />
    </Shell>
  );
};
