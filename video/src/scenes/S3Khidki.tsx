import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell } from "../components/Bits";
import { lineAt, prog, rise } from "../lib";
import { C, FONT_HI } from "../theme";

const ID = "s3_khidki" as const;

const Benefit: React.FC<{ who: string; what: string; frame: number; at: number; children: React.ReactNode }> = ({ who, what, frame, at, children }) => (
  <div style={{ width: 530, padding: "24px 32px 26px", borderRadius: 30, background: "rgba(238,240,230,0.08)", border: "2px solid rgba(238,240,230,0.2)", ...rise(frame, at, 18, 46) }}>
    <div style={{ fontSize: 34, fontWeight: 600, color: "#9CC8EA" }}>{who}</div>
    <div style={{ marginTop: 4, fontSize: 48, fontWeight: 800, lineHeight: 1.12 }}>{what}</div>
    <div style={{ marginTop: 16, height: 70, display: "flex", alignItems: "center" }}>{children}</div>
  </div>
);

/** The name, what it does, and who it helps. */
export const S3Khidki: React.FC = () => {
  const frame = useCurrentFrame();
  const does = lineAt(ID, 1);
  const helps = lineAt(ID, 2);
  const span = Math.max(lineAt(ID, 2, "end") - helps, 60);
  const lift = prog(frame, does - 14, 26);
  return (
    <Shell dark>
      <Audio src={staticFile("vo/s3_khidki.wav")} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 104 - lift * 62, textAlign: "center" }}>
        <div style={{ fontFamily: FONT_HI, fontSize: 250 - lift * 92, fontWeight: 800, lineHeight: 1.2, ...rise(frame, 0, 24, 70) }}>खिड़की</div>
        <div style={{ fontSize: 60 - lift * 12, fontWeight: 700, marginTop: -6, ...rise(frame, 10, 20) }}>
          Khidki <span style={{ fontWeight: 400, color: C.chalkSoft }}>is Hindi for window</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 110, right: 110, top: 326, textAlign: "center", fontSize: 72, fontWeight: 800, lineHeight: 1.15, ...rise(frame, does - 4, 20, 40) }}>
        It tells the teacher the exact minute
        <br />
        to open, and to close.
      </div>
      <div style={{ position: "absolute", left: 110, right: 110, top: 528, display: "flex", justifyContent: "space-between" }}>
        <Benefit who="For the children" what="Fresher air" frame={frame} at={helps - 4}>
          <svg width={420} height={84} viewBox="0 0 420 84">
            <path d="M4 14 C 90 16, 150 30, 210 52 S 340 74, 416 76" fill="none" stroke="#7FB8E3" strokeWidth={7} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - prog(frame, helps + 4, 36)} />
          </svg>
        </Benefit>
        <Benefit who="For the teacher" what="Fewer interruptions" frame={frame} at={helps + span * 0.34}>
          <div style={{ display: "flex", gap: 10 }}>
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} style={{ width: 44, height: 44, borderRadius: 12, background: i < 2 ? "#7FB8E3" : "rgba(238,240,230,0.16)", opacity: prog(frame, helps + span * 0.34 + 6 + i * 3, 8) }} />
            ))}
          </div>
        </Benefit>
        <Benefit who="For the principal" what="Every room, one page" frame={frame} at={helps + span * 0.62}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 44px)", gap: 8 }}>
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} style={{ height: 44, borderRadius: 6, border: "4px solid #7FB8E3", background: i === 3 ? "rgba(217,154,30,0.9)" : "transparent", opacity: prog(frame, helps + span * 0.62 + 6 + i * 3, 8) }} />
            ))}
          </div>
        </Benefit>
      </div>
      <Caption scene={ID} dark />
    </Shell>
  );
};
