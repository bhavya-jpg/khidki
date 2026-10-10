import { Audio } from "@remotion/media";
import { CanvasImage, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Caption, Shell } from "../components/Bits";
import { lerp, lineAt, prog, rise } from "../lib";
import { C, FONT_HI } from "../theme";

const ID = "s9_close" as const;

/** The no-hardware tier, the name once more, and what is real and what is not. */
export const S9Close: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const name = lineAt(ID, 1);
  const sheet = prog(frame, 0, 26);
  return (
    <Shell>
      <Audio src={staticFile("vo/s9_close.wav")} />
      <div
        style={{
          position: "absolute", left: 130, top: 96, width: 780, height: 582, borderRadius: 6, overflow: "hidden", background: "#fff",
          boxShadow: "0 50px 90px -40px rgba(31,58,48,0.6), 0 0 0 1px rgba(31,58,48,0.1)",
          opacity: sheet, rotate: `${lerp(-6, -2.5, sheet)}deg`, translate: `0px ${(1 - sheet) * 60}px`,
        }}
      >
        <CanvasImage src={staticFile("footage/print-sheet.png")} premountFor={fps} style={{ width: 780, height: 582 }} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 716, fontSize: 34, fontWeight: 600, color: C.ink2, ...rise(frame, 16) }}>
        No sensor, no tablet: today's window timetable on one A4 page
      </div>
      <div style={{ position: "absolute", left: 1040, top: 190, width: 780 }}>
        <div style={{ fontFamily: FONT_HI, fontSize: 190, fontWeight: 800, lineHeight: 1.2, color: C.breathInk, ...rise(frame, name - 6, 22, 50) }}>खिड़की</div>
        <div style={{ fontSize: 76, fontWeight: 800, lineHeight: 1.12, ...rise(frame, name + 6, 20) }}>
          Open the window
          <br />
          at the right minute.
        </div>
        <div style={{ marginTop: 26, fontSize: 38, fontWeight: 600, color: C.ink2, ...rise(frame, name + 22, 16) }}>github.com/bhavya-jpg/khidki</div>
      </div>
      <div style={{ position: "absolute", left: 120, right: 120, top: 800, fontSize: 26, lineHeight: 1.45, color: C.ink2, ...rise(frame, 24) }}>
        Simulated classroom and sensor; real outdoor air (CAMS via Open-Meteo, CC BY 4.0). The school is fictional. Narration is a synthetic voice made with
        Chatterbox. Built with Claude Code for Environmental Hacks 2026. Khidki is not a medical device.
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
