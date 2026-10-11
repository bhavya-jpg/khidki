import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell, Tag } from "../components/Bits";
import { Ribbon } from "../components/Ribbon";
import run from "../data/run.json";
import { lineAt, rise } from "../lib";
import { C } from "../theme";

const ID = "s4b_rules" as const;
const pe = run.decisions.find((d) => d.key === "pe:6B") ?? run.decisions[0];

/** The rule behind a decision. The plan and the decision are the real ones from this run. */
export const S4bRules: React.FC = () => {
  const frame = useCurrentFrame();
  const cedar = lineAt(ID, 0) + 6;
  return (
    <Shell>
      <Audio src={staticFile("vo/s4b_rules.wav")} />
      <Tag>Class 6B, the plan from this run</Tag>
      <div style={{ position: "absolute", left: 110, top: 84, ...rise(frame, 0) }}>
        <div style={{ fontSize: 110, fontWeight: 800, lineHeight: 1.05 }}>School rules, as code</div>
        <div style={{ marginTop: 6, fontSize: 44, fontWeight: 600, color: C.ink2 }}>Today's plan for Class 6B, and one decision with its policy</div>
      </div>
      <div style={{ position: "absolute", left: 110, top: 330 }}>
        <Ribbon width={1700} frame={frame} from={-200} over={10} />
      </div>
      <div
        style={{
          position: "absolute", left: 110, top: 556, width: 1700, display: "flex", gap: 0, borderRadius: 28, overflow: "hidden",
          boxShadow: "0 40px 80px -44px rgba(31,58,48,0.55)", ...rise(frame, cedar - 6, 20, 70),
        }}
      >
        <div style={{ flex: "0 0 720px", padding: "24px 34px", background: C.raised }}>
          <div style={{ fontSize: 28, fontWeight: 600, color: C.ink2 }}>Today's decision</div>
          <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 20 }}>
            <span style={{ fontSize: 54, fontWeight: 800 }}>{pe.label}</span>
            <span style={{ fontSize: 34, fontWeight: 700, padding: "6px 22px", borderRadius: 999, background: C.blackboard, color: C.chalk }}>{pe.outdoor ? "Outdoors" : "Indoors"}</span>
          </div>
          <div style={{ marginTop: 8, fontSize: 31, color: C.ink2, lineHeight: 1.3 }}>
            {pe.start}–{pe.end}. Forecast PM2.5 <b style={{ color: C.blackboard }}>{pe.max_pm25} µg/m³</b>, over the limit of 90.
          </div>
          <div style={{ marginTop: 10, fontSize: 30, fontWeight: 700, color: C.breathInk }}>Decided by policy {pe.policy_ids.filter((p) => p.startsWith("S")).join(", ")}</div>
        </div>
        <pre style={{ flex: 1, margin: 0, padding: "24px 34px", background: C.blackboard, color: C.chalk, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 26, lineHeight: 1.42, whiteSpace: "pre-wrap" }}>
          <span style={{ color: "#7FB8E3" }}>@id</span>("S2"){"\n"}
          <span style={{ color: "#7FB8E3" }}>forbid</span> (principal,{"\n"}
          {"  "}action == Khidki::Action::"activity.outdoor",{"\n"}
          {"  "}resource){"\n"}
          <span style={{ color: "#7FB8E3" }}>when</span> {"{ "}context.maxPm25During {">"} <b style={{ color: "#FFFFFF" }}>90</b>{" };"}
        </pre>
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
