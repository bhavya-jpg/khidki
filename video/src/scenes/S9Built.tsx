import { Audio } from "@remotion/media";
import { CanvasImage, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Caption, Shell, Tag } from "../components/Bits";
import { lineAt, rise } from "../lib";
import { C } from "../theme";

const ID = "s9_built" as const;

const Shot: React.FC<{ src: string; w: number; h: number; label: string; note: string; frame: number; at: number; fps: number }> = ({ src, w, h, label, note, frame, at, fps }) => (
  <div style={{ width: w, ...rise(frame, at, 18, 50) }}>
    <div style={{ width: w, height: h, borderRadius: 16, overflow: "hidden", background: "#fff", boxShadow: "0 40px 70px -40px rgba(31,58,48,0.6), 0 0 0 2px rgba(31,58,48,0.12)" }}>
      <CanvasImage src={staticFile(src)} premountFor={fps} style={{ width: w, height: h }} />
    </div>
    <div style={{ marginTop: 16, fontSize: 38, fontWeight: 800 }}>{label}</div>
    <div style={{ fontSize: 28, color: C.ink2 }}>{note}</div>
  </div>
);

/** What exists today: three real screens (screenshots from local mode), deployed and open. */
export const S9Built: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const l1 = lineAt(ID, 0), l1e = lineAt(ID, 0, "end"), l2 = lineAt(ID, 1);
  const span = l1e - l1;
  return (
    <Shell>
      <Audio src={staticFile("vo/s9_built.wav")} />
      <Tag>Screenshots of the working app</Tag>
      <div style={{ position: "absolute", left: 110, top: 78, fontSize: 100, fontWeight: 800, lineHeight: 1, ...rise(frame, 0) }}>What we built</div>
      <div style={{ position: "absolute", left: 110, top: 232, width: 1700, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Shot src="footage/teacher.png" w={548} h={342} label="The teacher's screen" note="one instruction, one tap" frame={frame} at={l1 + span * 0.22} fps={fps} />
        <Shot src="footage/principal-1x.png" w={548} h={342} label="The principal's page" note="every decision with its rule" frame={frame} at={l1 + span * 0.45} fps={fps} />
        <Shot src="footage/print-sheet.png" w={458} h={342} label="A timetable to print" note="for a school with no sensor at all" frame={frame} at={l1 + span * 0.66} fps={fps} />
      </div>
      <div style={{ position: "absolute", left: 110, top: 730, display: "flex", gap: 20, ...rise(frame, l2 - 2, 16, 30) }}>
        <span style={{ padding: "14px 30px", borderRadius: 18, background: C.blackboard, color: C.chalk, fontSize: 40, fontWeight: 800 }}>Deployed on AWS</span>
        <span style={{ padding: "14px 30px", borderRadius: 18, border: `3px solid ${C.blackboard}`, fontSize: 40, fontWeight: 800 }}>Open source: github.com/bhavya-jpg/khidki</span>
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
