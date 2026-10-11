import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell } from "../components/Bits";
import { lineAt, prog, rise } from "../lib";
import { C, FONT } from "../theme";

const ID = "s7_arch" as const;
type Box = { x: number; y: number; w: number; h: number; title: string; sub: string; aws: boolean };
const B: Record<string, Box> = {
  meter: { x: 0, y: 16, w: 310, h: 136, title: "Classroom CO₂ meter", sub: "simulated in this demo", aws: false },
  tablet: { x: 0, y: 214, w: 310, h: 128, title: "Teacher's tablet", sub: "React, on Amplify", aws: false },
  principal: { x: 0, y: 404, w: 310, h: 128, title: "Principal's page", sub: "decisions, overrides", aws: false },
  api: { x: 440, y: 222, w: 250, h: 112, title: "API Gateway", sub: "HTTP API", aws: true },
  lambda: { x: 820, y: 150, w: 370, h: 256, title: "AWS Lambda", sub: "physics twin and planner", aws: true },
  ddb: { x: 1330, y: 30, w: 370, h: 112, title: "DynamoDB", sub: "plans, readings, instructions", aws: true },
  sfn: { x: 1330, y: 222, w: 370, h: 112, title: "Step Functions", sub: "tap, wait, verify", aws: true },
  polly: { x: 1330, y: 414, w: 370, h: 112, title: "Amazon Polly", sub: "the instruction, in Hindi", aws: true },
  evb: { x: 820, y: 462, w: 370, h: 116, title: "EventBridge", sub: "Scheduler: 06:00, India time", aws: true },
};
const mid = (b: Box, side: "l" | "r" | "t" | "b"): [number, number] =>
  side === "l" ? [b.x, b.y + b.h / 2] : side === "r" ? [b.x + b.w, b.y + b.h / 2] : side === "t" ? [b.x + b.w / 2, b.y] : [b.x + b.w / 2, b.y + b.h];

/** The deployed architecture, drawn in the order the narration walks it. Every box is in the CDK stack. */
export const S7Arch: React.FC = () => {
  const frame = useCurrentFrame();
  const l1 = lineAt(ID, 0), l1e = lineAt(ID, 0, "end"), l2 = lineAt(ID, 1), l2e = lineAt(ID, 1, "end"), l3 = lineAt(ID, 2);
  const a = (k: number) => l1 + (l1e - l1) * k, b = (k: number) => l2 + (l2e - l2) * k;
  const at: Record<string, number> = { meter: a(0.3), api: a(0.42), lambda: a(0.6), ddb: a(0.8), tablet: a(0.36), principal: a(0.4), evb: b(0.02), sfn: b(0.36), polly: b(0.7) };
  const edges: [string, [number, number], [number, number], number][] = [
    ["meter-api", mid(B.meter, "r"), [B.api.x, B.api.y + 28], at.api],
    ["tablet-api", mid(B.tablet, "r"), mid(B.api, "l"), at.api],
    ["principal-api", mid(B.principal, "r"), [B.api.x, B.api.y + B.api.h - 28], at.api],
    ["api-lambda", mid(B.api, "r"), mid(B.lambda, "l"), at.lambda],
    ["lambda-ddb", [B.lambda.x + B.lambda.w, B.lambda.y + 50], mid(B.ddb, "l"), at.ddb],
    ["lambda-sfn", mid(B.lambda, "r"), mid(B.sfn, "l"), at.sfn],
    ["lambda-polly", [B.lambda.x + B.lambda.w, B.lambda.y + B.lambda.h - 50], mid(B.polly, "l"), at.polly],
    ["evb-lambda", mid(B.evb, "t"), mid(B.lambda, "b"), at.evb + 8],
  ];
  const cdk = prog(frame, l3 - 4, 20);
  // a reading travelling from the meter to the table
  const trip = prog(frame, a(0.42), (l1e - l1) * 0.5);
  const path: [number, number][] = [mid(B.meter, "r"), [B.api.x, B.api.y + 28], mid(B.api, "r"), mid(B.lambda, "l"), [B.lambda.x + B.lambda.w, B.lambda.y + 50], mid(B.ddb, "l")];
  const seg = Math.min(Math.floor(trip * (path.length - 1)), path.length - 2);
  const k = trip * (path.length - 1) - seg;
  const dot: [number, number] = [path[seg][0] + (path[seg + 1][0] - path[seg][0]) * k, path[seg][1] + (path[seg + 1][1] - path[seg][1]) * k];
  return (
    <Shell>
      <Audio src={staticFile("vo/s7_arch.wav")} />
      <div style={{ position: "absolute", left: 110, top: 70, fontSize: 104, fontWeight: 800, lineHeight: 1, ...rise(frame, 0) }}>How it is built, on AWS</div>
      <div style={{ position: "absolute", left: 110, top: 232, width: 1700, height: 600 }}>
        <div style={{ position: "absolute", left: 400, top: -12, width: 1326, height: 606, borderRadius: 30, border: `3px dashed ${C.ink3}`, opacity: cdk }} />
        <div style={{ position: "absolute", left: 432, top: 8, fontSize: 30, fontWeight: 700, color: C.ink2, whiteSpace: "nowrap", opacity: cdk }}>One AWS CDK app, region ap-southeast-2</div>
        <svg width={1700} height={600} viewBox="0 0 1700 600" style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
          {edges.map(([key, p, q, when]) => (
            <line key={key} x1={p[0]} y1={p[1]} x2={q[0]} y2={q[1]} stroke={C.ink3} strokeWidth={4} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - prog(frame, when - 6, 14)} />
          ))}
          <circle cx={dot[0]} cy={dot[1]} r={13} fill={C.breath} opacity={trip > 0 && trip < 1 ? 1 : 0} />
        </svg>
        {Object.entries(B).map(([key, box]) => (
          <div
            key={key}
            style={{
              position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h, boxSizing: "border-box", padding: "16px 22px", borderRadius: 20, fontFamily: FONT,
              background: box.aws ? C.raised : "transparent", border: box.aws ? "none" : `3px solid ${C.rule}`, borderTop: box.aws ? `6px solid ${C.blackboard}` : `3px solid ${C.rule}`,
              boxShadow: box.aws ? "0 26px 50px -36px rgba(31,58,48,0.55)" : "none", ...rise(frame, at[key] - 6, 14, 26),
            }}
          >
            <div style={{ fontSize: 34, fontWeight: 800, lineHeight: 1.1 }}>{box.title}</div>
            <div style={{ marginTop: 6, fontSize: 26, color: C.ink2, lineHeight: 1.2 }}>{box.sub}</div>
            {key === "lambda" && (
              <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 10 }}>
                <span style={{ padding: "8px 16px", borderRadius: 12, background: C.blackboard, color: C.chalk, fontSize: 26, fontWeight: 700, width: "fit-content" }}>Cedar policies</span>
                <span style={{ fontSize: 24, color: C.ink2 }}>API, ingest, planner, workflow task</span>
              </div>
            )}
          </div>
        ))}
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
