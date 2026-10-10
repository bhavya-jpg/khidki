import { interpolateColors, random, useCurrentFrame } from "remotion";
import { C } from "../theme";

/**
 * The classroom window, drawn for video. Same honesty rule as the product: one dot ≈ 2 µg/m³ of PM2.5,
 * outside dots behind the glass, room dots in front, and a warm haze whose strength follows CO₂.
 */
export const WindowArt: React.FC<{
  outPm: number;
  inPm: number;
  co2: number;
  openLeft?: number; // 0 shut … 1 fully open (road side)
  openRight?: number; // corridor side
  width?: number;
  seed?: string;
}> = ({ outPm, inPm, co2, openLeft = 0, openRight = 0, width = 800, seed = "w" }) => {
  const frame = useCurrentFrame();
  const W = 800, H = 600;
  const X0 = 44, Y0 = 44, X1 = 756, Y1 = 512; // the opening
  const ow = X1 - X0, oh = Y1 - Y0, mid = (X0 + X1) / 2;
  const smog = Math.min(outPm / 300, 1);
  const skyTop = interpolateColors(smog, [0, 1], ["#8FBBDD", "#A7A792"]);
  const skyBottom = interpolateColors(smog, [0, 1], ["#DCEAF0", "#D6AE62"]);
  const nOut = Math.round(outPm / 2);
  const nIn = Math.round(inPm / 2);
  const haze = Math.max(0, Math.min((co2 - 400) / 2000, 1));

  const dot = (i: number, layer: string, n: number) => {
    const rx = random(`${seed}${layer}x${i}`), ry = random(`${seed}${layer}y${i}`), rs = random(`${seed}${layer}s${i}`);
    const speed = layer === "in" ? 0.22 + rs * 0.2 : 0.1 + rs * 0.12;
    const x = X0 + ((rx * ow + Math.sin(frame / 46 + rs * 9) * 10 + (layer === "in" ? frame * 0.12 * (openLeft + openRight) : 0)) % ow + ow) % ow;
    const y = Y0 + ((ry * oh + frame * speed) % oh);
    return { x, y, r: layer === "in" ? 3.4 + rs * 2.2 : 2.2 + rs * 1.8, key: `${layer}${i}`, show: i < n };
  };

  // a casement leaf: hinged on its outer edge, free edge swings toward the viewer
  const leaf = (side: "L" | "R", open: number) => {
    const theta = open * 1.15; // radians, up to about 66°
    const w = ow / 2 - 4;
    const hinge = side === "L" ? X0 : X1;
    const dir = side === "L" ? 1 : -1;
    const fx = hinge + dir * w * Math.cos(theta);
    const grow = Math.sin(theta) * 26;
    const pts = `${hinge},${Y0} ${fx},${Y0 - grow} ${fx},${Y1 + grow} ${hinge},${Y1}`;
    const barY0 = (Y0 + Y1) / 2;
    return (
      <g key={side}>
        <polygon points={pts} fill="rgba(255,255,255,0.10)" />
        <line x1={hinge + dir * w * Math.cos(theta) * 0.18} y1={Y0 + 130} x2={hinge + dir * w * Math.cos(theta) * 0.5} y2={Y0 + 30} stroke="rgba(255,255,255,0.5)" strokeWidth={3} />
        <line x1={hinge + dir * w * Math.cos(theta) * 0.26} y1={Y0 + 170} x2={hinge + dir * w * Math.cos(theta) * 0.62} y2={Y0 + 50} stroke="rgba(255,255,255,0.3)" strokeWidth={2} />
        <polygon points={pts} fill="none" stroke={C.blackboard} strokeWidth={13} strokeLinejoin="miter" />
        <line x1={hinge} y1={barY0} x2={fx} y2={barY0} stroke={C.blackboard} strokeWidth={9} />
      </g>
    );
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={width} height={(width * H) / W} style={{ display: "block", overflow: "visible" }}>
      <defs>
        <linearGradient id={`${seed}-sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={skyTop} />
          <stop offset="1" stopColor={skyBottom} />
        </linearGradient>
        <linearGradient id={`${seed}-haze`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="rgba(232,196,120,0)" />
          <stop offset="1" stopColor="rgba(226,178,92,0.95)" />
        </linearGradient>
        <clipPath id={`${seed}-clip`}><rect x={X0} y={Y0} width={ow} height={oh} /></clipPath>
      </defs>
      <rect x={10} y={10} width={W - 20} height={H - 30} fill={C.blackboard} rx={4} />
      <g clipPath={`url(#${seed}-clip)`}>
        <rect x={X0} y={Y0} width={ow} height={oh} fill={`url(#${seed}-sky)`} />
        <circle cx={X0 + ow * 0.66} cy={Y0 + oh * 0.3} r={46} fill="#FFF6DA" opacity={0.9 - smog * 0.62} />
        <circle cx={X0 + ow * 0.66} cy={Y0 + oh * 0.3} r={92} fill="#FFF6DA" opacity={0.22 - smog * 0.1} />
        {[[0, 70, 54], [62, 96, 60], [130, 60, 90], [228, 128, 74], [310, 84, 108], [426, 110, 62], [496, 150, 96], [600, 92, 70], [676, 60, 50]].map(([x, h, w], i) => (
          <rect key={i} x={X0 + x} y={Y1 - h} width={w} height={h} fill={C.ink2} opacity={0.34 - smog * 0.2} />
        ))}
        {Array.from({ length: 150 }, (_, i) => dot(i, "out", nOut)).map((d) => d.show && <circle key={d.key} cx={d.x} cy={d.y} r={d.r} fill="rgba(58,46,24,0.5)" />)}
      </g>
      {leaf("L", openLeft)}
      {leaf("R", openRight)}
      <g clipPath={`url(#${seed}-clip)`}>
        <rect x={X0} y={Y0 + oh * 0.35} width={ow} height={oh * 0.65} fill={`url(#${seed}-haze)`} opacity={haze * 0.8} />
        {Array.from({ length: 150 }, (_, i) => dot(i, "in", nIn)).map((d) => d.show && <circle key={d.key} cx={d.x} cy={d.y} r={d.r} fill="rgba(46,38,24,0.72)" />)}
      </g>
      <rect x={mid - 7} y={Y0} width={14} height={oh} fill={C.blackboard} />
      <rect x={X0} y={Y0} width={ow} height={oh} fill="none" stroke={C.blackboard} strokeWidth={14} />
      <rect x={0} y={H - 44} width={W} height={26} fill={C.blackboard} rx={3} />
      <rect x={0} y={H - 48} width={W} height={6} fill="#3A5A4D" />
    </svg>
  );
};
