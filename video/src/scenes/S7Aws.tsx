import { Audio } from "@remotion/media";
import { staticFile, useCurrentFrame } from "remotion";
import { Caption, Shell } from "../components/Bits";
import { lineAt, rise } from "../lib";
import { C } from "../theme";

const ID = "s7_aws" as const;

/** Where AWS fits. Names and roles only: every one of these is deployed and in the repository's CDK stack. */
export const S7Aws: React.FC = () => {
  const frame = useCurrentFrame();
  const l1 = lineAt(ID, 0), l1e = lineAt(ID, 0, "end"), l2 = lineAt(ID, 1), l2e = lineAt(ID, 1, "end"), l3 = lineAt(ID, 2);
  const a = (k: number) => l1 + (l1e - l1) * k, b = (k: number) => l2 + (l2e - l2) * k;
  const cards: [string, string, number][] = [
    ["AWS Step Functions", "waits for the tap, then verifies", 4],
    ["AWS Lambda", "planner, API and ingest", a(0.3)],
    ["Amazon API Gateway", "the tablet and the sensor talk here", a(0.5)],
    ["Amazon DynamoDB", "plans, readings, instructions", a(0.68)],
    ["Amazon EventBridge", "starts the 06:00 plan, India time", b(0.02)],
    ["Amazon Polly", "the instruction, spoken in Hindi", b(0.42)],
    ["Cedar", "school safety rules as policy code", b(0.66)],
    ["AWS CDK", "the whole stack as code", l3 + 6],
  ];
  return (
    <Shell>
      <Audio src={staticFile("vo/s7_aws.wav")} />
      <div style={{ position: "absolute", left: 110, top: 84, fontSize: 124, fontWeight: 800, lineHeight: 1, ...rise(frame, 0) }}>Built on AWS</div>
      <div style={{ position: "absolute", left: 110, top: 262, width: 1700 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20 }}>
          {cards.map(([name, role, at]) => (
            <div key={name} style={{ padding: "24px 28px 28px", borderRadius: 24, background: C.raised, borderTop: `6px solid ${C.blackboard}`, minHeight: 176, boxShadow: "0 30px 60px -44px rgba(31,58,48,0.5)", ...rise(frame, at, 14, 40) }}>
              <div style={{ fontSize: 40, fontWeight: 800, lineHeight: 1.1 }}>{name}</div>
              <div style={{ marginTop: 10, fontSize: 30, color: C.ink2, lineHeight: 1.28 }}>{role}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 26, fontSize: 30, color: C.ink2, ...rise(frame, l3 + 16) }}>
          Also in the stack: Amazon S3, Parameter Store, Amplify Hosting, CloudWatch. Region ap-southeast-2.
        </div>
      </div>
      <Caption scene={ID} />
    </Shell>
  );
};
