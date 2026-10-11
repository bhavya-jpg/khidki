import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell } from "../components/Bits";
import { rise } from "../lib";
import { C, FONT_HI } from "../theme";

const ID = "s10_close" as const;

/** The name once more, and what is real and what is not. */
export const S10Close: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Shell dark>
      <Audio src={staticFile("vo/s10_close.wav")} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center" }}>
        <div style={{ fontFamily: FONT_HI, fontSize: 240, fontWeight: 800, lineHeight: 1.2, ...rise(frame, 0, 22, 60) }}>खिड़की</div>
        <div style={{ marginTop: 4, fontSize: 84, fontWeight: 800, lineHeight: 1.12, ...rise(frame, 10, 20) }}>Open the window at the right minute.</div>
        <div style={{ marginTop: 26, fontSize: 40, fontWeight: 600, color: C.chalkSoft, ...rise(frame, 22, 16) }}>github.com/bhavya-jpg/khidki</div>
      </div>
      <div style={{ position: "absolute", left: 200, right: 200, top: 722, textAlign: "center", fontSize: 27, lineHeight: 1.45, color: C.chalkSoft, ...rise(frame, 30) }}>
        Simulated classroom and CO₂ meter; real outdoor air (CAMS via Open-Meteo, CC BY 4.0). The school is fictional. Results are a simulation, not a field
        trial. The narration is a synthetic voice made with Chatterbox. Built with Claude Code for Environmental Hacks 2026. Khidki is not a medical device.
      </div>
      <Caption scene={ID} dark />
    </Shell>
  );
};
