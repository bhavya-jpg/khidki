import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell, Tag } from "../components/Bits";
import { WindowArt } from "../components/WindowArt";
import { lerp, lineAt, num, prog, rise } from "../lib";
import { C } from "../theme";

const ID = "s2_dilemma" as const;

const Side: React.FC<{ title: string; value: string; unit: string; note: string; noteAt: number; frame: number; at: number; children: React.ReactNode }> = ({
  title, value, unit, note, noteAt, frame, at, children,
}) => (
  <div style={{ width: 800, ...rise(frame, at, 20, 50) }}>
    <div style={{ fontSize: 58, fontWeight: 800 }}>{title}</div>
    <div style={{ marginTop: 18, padding: 26, borderRadius: 30, background: "linear-gradient(180deg, #F7F8F2, #E4E0D0)", boxShadow: "0 40px 70px -40px rgba(31,58,48,0.5)", width: "fit-content" }}>
      {children}
    </div>
    <div style={{ marginTop: 22, display: "flex", alignItems: "baseline", gap: 18 }}>
      <span style={{ fontSize: 112, fontWeight: 800, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{value}</span>
      <span style={{ fontSize: 34, fontWeight: 500, color: C.ink2, maxWidth: 420, lineHeight: 1.25 }}>{unit}</span>
    </div>
    <div style={{ marginTop: 8, fontSize: 38, fontWeight: 600, color: C.ink2, ...rise(frame, noteAt, 14, 20) }}>{note}</div>
  </div>
);

/** Shut: CO₂ climbs. Open: the smog comes in. Numbers from Khidki's physics model. */
export const S2Dilemma: React.FC = () => {
  const frame = useCurrentFrame();
  const shutEnd = lineAt(ID, 0, "end");
  const stuffy = lineAt(ID, 1);
  const open = lineAt(ID, 2);
  const climb = prog(frame, 10, shutEnd - 20);
  const swing = prog(frame, open + 4, 34);
  return (
    <Shell>
      <Audio src={staticFile("vo/s2_dilemma.wav")} />
      <Tag>Physics model: 44 children, outdoor PM2.5 250 µg/m³</Tag>
      <div style={{ position: "absolute", left: 110, top: 118, display: "flex", gap: 100 }}>
        <Side title="Keep it shut" frame={frame} at={0} value={num(lerp(520, 2380, climb))} unit="ppm CO₂ after one 40-minute period" note="The room turns stuffy. Attention drops." noteAt={stuffy}>
          <WindowArt seed="s2a" width={520} outPm={250} inPm={156} co2={lerp(520, 2380, climb)} />
        </Side>
        <Side title="Open it" frame={frame} at={open - 8} value={num(lerp(156, 242, swing))} unit="µg/m³ PM2.5 in the room" note="97% of the smog outside comes in." noteAt={open + 30}>
          <WindowArt seed="s2b" width={520} outPm={250} inPm={lerp(156, 242, swing)} co2={lerp(2380, 1030, swing)} openLeft={swing} openRight={swing} />
        </Side>
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
