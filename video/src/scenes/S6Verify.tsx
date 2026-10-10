import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Device, Shell, Tag } from "../components/Bits";
import { Chain } from "../components/Chain";
import { Curve } from "../components/Curve";
import cap from "../data/capture.json";
import run from "../data/run.json";
import { lineAt, rise } from "../lib";
import { C } from "../theme";

const ID = "s6_verify" as const;
const CAPTURE_SPEED = 12; // the simulator ran at 12× while the clips were captured (scripts/capture.mjs)
const hhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
const both = run.timetable.find((r) => r.window === "open_both");
const ASKED = both?.t ?? "08:35";
const ASKED_MIN = Number(ASKED.slice(0, 2)) * 60 + Number(ASKED.slice(3));
const f = cap.clips.followup.marks;
const BOTH = hhmm(ASKED_MIN + Math.round(((f.tap2 - f.instruction) * CAPTURE_SPEED) / 60));

/**
 * Verification: one real clip of the "open both sides" instruction, beside the real CO₂ readings, then the
 * workflow that runs it. The clip was 41 s long; scripts/edit-footage.mjs plays its waiting faster so the
 * follow-up and the tick land on the narration, and the scene says so.
 */
export const S6Verify: React.FC = () => {
  const frame = useCurrentFrame();
  const curveAt = lineAt(ID, 1) - 12;
  const sf = lineAt(ID, 3);
  const sfSpan = lineAt(ID, 3, "end") - sf;
  return (
    <Shell>
      <Audio src={staticFile("vo/s6_verify.wav")} />
      <Tag>Real screen and readings from this run. Simulated sensor.</Tag>
      <div style={{ position: "absolute", left: 110, top: 122 }}>
        <Device width={900} clips={[{ src: "footage/verify-edit.mp4" }]} />
        <div style={{ marginTop: 12, fontSize: 24, color: C.ink2 }}>The minutes of waiting for the air are played faster than real time.</div>
      </div>
      <div style={{ position: "absolute", left: 1060, top: 122, width: 750, padding: "26px 28px 18px", borderRadius: 28, background: C.raised, boxShadow: "0 40px 80px -46px rgba(31,58,48,0.5)", ...rise(frame, curveAt - 10, 18, 40) }}>
        <div style={{ fontSize: 40, fontWeight: 800 }}>CO₂ in the room, ppm</div>
        <div style={{ fontSize: 26, color: C.ink2, marginBottom: 6 }}>The children's breath is the tracer gas</div>
        <Curve width={694} height={400} frame={frame} from={curveAt} over={lineAt(ID, 2, "end") - curveAt} askedAt={ASKED} bothAt={BOTH} />
      </div>
      <div style={{ position: "absolute", left: 110, top: 752, ...rise(frame, sf - 8, 16, 30) }}>
        <div style={{ fontSize: 30, fontWeight: 700, marginBottom: 14 }}>
          AWS Step Functions <span style={{ fontWeight: 400, color: C.ink2 }}>state machine Khidki-NudgeSM, as deployed</span>
        </div>
        <Chain
          frame={frame}
          from={sf + 4}
          over={sfSpan * 0.85}
          states={["IssueNudge", "TeacherTapped", "WaitThenVerify", "VerifyFromCO2", "AirChanged", "FollowUpNudge", "Verified"]}
          notes={{ IssueNudge: "waits for the tap", WaitThenVerify: "waits for the air", VerifyFromCO2: "fits the curve", FollowUpNudge: "asks for the other side" }}
        />
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
