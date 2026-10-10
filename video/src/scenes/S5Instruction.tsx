import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Device, Shell, Tag } from "../components/Bits";
import cap from "../data/capture.json";
import { lineAt, rise } from "../lib";
import { C } from "../theme";

const ID = "s5_instruction" as const;
/** Real footage: the instruction arrives, the teacher taps once. scripts/edit-footage.mjs times the clip so the tap lands on "One tap". */
export const S5Instruction: React.FC = () => {
  const frame = useCurrentFrame();
  const six = lineAt(ID, 2);
  return (
    <Shell>
      <Audio src={staticFile("vo/s5_instruction.wav")} />
      <Tag>Real screen, local mode: simulated classroom</Tag>
      <div style={{ position: "absolute", left: 110, top: 124, ...rise(frame, 0, 20, 50) }}>
        <Device width={1180} clips={[{ src: "footage/instruction-edit.mp4" }]} />
      </div>
      <div style={{ position: "absolute", left: 1350, top: 170, width: 470 }}>
        <div style={{ fontSize: 30, fontWeight: 600, color: C.ink2, ...rise(frame, 10) }}>The teacher's tablet, Class 6B</div>
        <div style={{ marginTop: 14, fontSize: 64, fontWeight: 800, lineHeight: 1.12, ...rise(frame, 16) }}>One calm instruction</div>
        <div style={{ marginTop: 18, fontSize: 36, color: C.ink2, lineHeight: 1.35, ...rise(frame, 26) }}>
          “{cap.first.text.en}”, and one line of why: “{cap.first.reason.en.split(".")[0]}.”
        </div>
        <div style={{ marginTop: 44, padding: "24px 28px", borderRadius: 24, background: C.blackboard, color: C.chalk, ...rise(frame, six - 4, 16, 40) }}>
          <div style={{ fontSize: 96, fontWeight: 800, lineHeight: 1 }}>6</div>
          <div style={{ marginTop: 6, fontSize: 34, fontWeight: 600 }}>requests a day, at most</div>
        </div>
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
