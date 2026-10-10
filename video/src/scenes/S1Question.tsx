import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell, Tag } from "../components/Bits";
import { WindowArt } from "../components/WindowArt";
import run from "../data/run.json";
import { lerp, lineAt, prog, rise } from "../lib";
import { C, FONT_HI } from "../theme";

const ID = "s1_question" as const;

/** The question: a bad-air morning, one classroom, one window. */
export const S1Question: React.FC = () => {
  const frame = useCurrentFrame();
  const ask = lineAt(ID, 1);
  return (
    <Shell dark>
      <Audio src={staticFile("vo/s1_question.wav")} />
      <Tag dark>Real outdoor air, simulated classroom</Tag>
      <div style={{ position: "absolute", left: 110, top: 150, width: 900 }}>
        <div style={{ display: "flex", gap: 16, alignItems: "center", ...rise(frame, 4) }}>
          <span style={{ fontSize: 34, fontWeight: 600, color: C.chalkSoft }}>East Delhi, 18 November 2025</span>
          <span style={{ fontSize: 30, fontWeight: 700, padding: "6px 18px", borderRadius: 999, background: "rgba(238,240,230,0.14)" }}>
            AQI {run.outdoor.aqi}, {run.outdoor.category_en}
          </span>
        </div>
        <div style={{ marginTop: 22, fontSize: 46, fontWeight: 500, color: C.chalkSoft, ...rise(frame, 14) }}>
          One teacher. 44 children. One question.
        </div>
        <div style={{ marginTop: 70, fontFamily: FONT_HI, fontSize: 150, fontWeight: 800, lineHeight: 1.24, ...rise(frame, ask - 6, 22, 60) }}>
          खिड़की खोलें,
          <br />
          या बंद रखें?
        </div>
        <div style={{ marginTop: 26, fontSize: 60, fontWeight: 600, color: C.chalkSoft, ...rise(frame, ask + 6, 20) }}>
          Open the window, or keep it shut?
        </div>
      </div>
      <div
        style={{
          position: "absolute", left: 1090, top: 210, padding: 34, borderRadius: 34,
          background: "linear-gradient(180deg, #F7F8F2, #E4E0D0)", boxShadow: "0 60px 110px -50px rgba(0,0,0,0.75)",
          opacity: prog(frame, 0, 20), scale: String(lerp(0.96, 1, prog(frame, 0, 40))),
        }}
      >
        <WindowArt seed="s1" width={660} outPm={run.outdoor.pm25} inPm={100} co2={lerp(700, 1500, prog(frame, 0, 260))} />
      </div>
      <Caption scene={ID} dark />
    </Shell>
  );
};
