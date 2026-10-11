import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell } from "../components/Bits";
import { lineAt, rise } from "../lib";
import { C } from "../theme";

const ID = "s7b_stack" as const;

const Card: React.FC<{ part: string; tech: string[]; how: string; frame: number; at: number }> = ({ part, tech, how, frame, at }) => (
  <div style={{ padding: "26px 30px 30px", borderRadius: 26, background: C.raised, borderTop: `6px solid ${C.breathInk}`, boxShadow: "0 30px 60px -44px rgba(31,58,48,0.5)", ...rise(frame, at, 14, 40) }}>
    <div style={{ fontSize: 30, fontWeight: 600, color: C.ink2 }}>{part}</div>
    <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 10 }}>
      {tech.map((t) => (
        <span key={t} style={{ padding: "6px 18px", borderRadius: 12, background: C.blackboard, color: C.chalk, fontSize: 34, fontWeight: 700 }}>{t}</span>
      ))}
    </div>
    <div style={{ marginTop: 14, fontSize: 31, lineHeight: 1.28 }}>{how}</div>
  </div>
);

/** The rest of the stack, as it is in the repository. */
export const S7bStack: React.FC = () => {
  const frame = useCurrentFrame();
  const l1 = lineAt(ID, 0), l1e = lineAt(ID, 0, "end"), l2 = lineAt(ID, 1), l3 = lineAt(ID, 2);
  return (
    <Shell>
      <Audio src={staticFile("vo/s7b_stack.wav")} />
      <div style={{ position: "absolute", left: 110, top: 76, fontSize: 110, fontWeight: 800, lineHeight: 1, ...rise(frame, 0) }}>Under the hood</div>
      <div style={{ position: "absolute", left: 110, top: 240, width: 1700, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22 }}>
        <Card part="The twin and the planner" tech={["Python", "NumPy"]} how="Dynamic programming over the day, in 5-minute steps." frame={frame} at={l1 + 4} />
        <Card part="The window check" tech={["Least-squares fit"]} how="Fits the room's air-change rate to the CO₂ curve." frame={frame} at={l1 + (l1e - l1) * 0.66} />
        <Card part="The screens" tech={["React", "TypeScript", "Vite"]} how="A canvas window where one dot ≈ 2 µg/m³ of PM2.5." frame={frame} at={l2 - 2} />
        <Card part="Proof" tech={["131 tests", "FastAPI local mode"]} how="Everything also runs on a laptop, with no cloud account." frame={frame} at={l3 - 2} />
      </div>
      <div style={{ position: "absolute", left: 110, top: 812, fontSize: 28, color: C.ink2, ...rise(frame, l3 + 20) }}>
        Outdoor air: CAMS via Open-Meteo (CC BY 4.0). Policies: Cedar. Infrastructure: AWS CDK. Built with Claude Code.
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
