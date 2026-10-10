import { Video } from "@remotion/media";
import { AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { prog, VO, type SceneId } from "../lib";
import { C, FONT } from "../theme";

/** The narration as a caption, one sentence at a time, timed from the generated audio. */
export const Caption: React.FC<{ scene: SceneId; dark?: boolean }> = ({ scene, dark = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const line = VO[scene].lines.find((l) => t >= l.start - 0.1 && t < l.end + 0.28);
  if (!line) return null;
  const a = Math.min(prog(frame, Math.round((line.start - 0.1) * fps), 6), 1 - prog(frame, Math.round((line.end + 0.1) * fps), 5));
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 54, pointerEvents: "none" }}>
      <div
        style={{
          maxWidth: 1720, padding: "16px 34px", borderRadius: 18, opacity: a,
          background: dark ? "rgba(238,240,230,0.94)" : "rgba(31,58,48,0.94)", color: dark ? C.blackboard : C.chalk,
          fontFamily: FONT, fontSize: 40, fontWeight: 500, lineHeight: 1.3, textAlign: "center",
        }}
      >
        {line.text}
      </div>
    </AbsoluteFill>
  );
};

/** A small, constant honesty label for every scene that shows the product or its numbers. */
export const Tag: React.FC<{ children: React.ReactNode; dark?: boolean }> = ({ children, dark = false }) => (
  <div
    style={{
      position: "absolute", top: 48, right: 80, padding: "10px 20px", borderRadius: 999, fontFamily: FONT, fontSize: 26, fontWeight: 500,
      color: dark ? C.chalkSoft : C.ink2, border: `2px solid ${dark ? "rgba(238,240,230,0.35)" : C.rule}`,
    }}
  >
    {children}
  </div>
);

export type Clip = { src: string; from?: number; durationInFrames?: number; trimBeforeFrames?: number; playbackRate?: number };

/** A plain tablet frame holding real screen footage. Clips are stacked, so a later one replaces an earlier one. */
export const Device: React.FC<{ width: number; clips: Clip[] }> = ({ width, clips }) => {
  const { fps } = useVideoConfig();
  const bezel = Math.round(width * 0.018);
  const inner = width - bezel * 2;
  return (
    <div style={{ width, padding: bezel, borderRadius: bezel * 2.2, background: "#16261F", boxShadow: "0 50px 90px -40px rgba(0,0,0,0.55), 0 0 0 2px rgba(255,255,255,0.06) inset" }}>
      <div style={{ width: inner, height: (inner * 900) / 1440, borderRadius: bezel * 0.9, overflow: "hidden", background: C.chalk, position: "relative" }}>
        {clips.map((c, i) => (
          <Video
            key={i}
            src={staticFile(c.src)}
            muted
            from={c.from ?? 0}
            durationInFrames={c.durationInFrames}
            trimBefore={c.trimBeforeFrames ?? 0}
            playbackRate={c.playbackRate ?? 1}
            premountFor={fps}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ))}
      </div>
    </div>
  );
};

export const Shell: React.FC<{ dark?: boolean; children: React.ReactNode }> = ({ dark = false, children }) => (
  <AbsoluteFill
    style={{
      fontFamily: FONT, color: dark ? C.chalk : C.blackboard,
      background: dark
        ? `radial-gradient(120% 90% at 85% 0%, #24483F 0%, ${C.blackboard} 55%), ${C.blackboard}`
        : `radial-gradient(110% 80% at 20% 0%, #F6F7F0 0%, ${C.chalk} 60%), ${C.chalk}`,
    }}
  >
    {children}
  </AbsoluteFill>
);
