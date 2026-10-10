import { Composition, Folder } from "remotion";
import { Explainer } from "./Explainer";
import { FPS, sceneFrames, totalFrames } from "./lib";
import { S1Question } from "./scenes/S1Question";
import { S2Dilemma } from "./scenes/S2Dilemma";
import { S3Khidki } from "./scenes/S3Khidki";
import { S4Plan } from "./scenes/S4Plan";
import { S5Instruction } from "./scenes/S5Instruction";
import { S6Verify } from "./scenes/S6Verify";
import { S7Aws } from "./scenes/S7Aws";
import { S8Results } from "./scenes/S8Results";
import { S9Close } from "./scenes/S9Close";

const size = { width: 1920, height: 1080, fps: FPS } as const;

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Khidki" component={Explainer} durationInFrames={totalFrames()} {...size} />
    <Folder name="Scenes">
      <Composition id="S1-Question" component={S1Question} durationInFrames={sceneFrames("s1_question")} {...size} />
      <Composition id="S2-Dilemma" component={S2Dilemma} durationInFrames={sceneFrames("s2_dilemma")} {...size} />
      <Composition id="S3-Khidki" component={S3Khidki} durationInFrames={sceneFrames("s3_khidki")} {...size} />
      <Composition id="S4-Plan" component={S4Plan} durationInFrames={sceneFrames("s4_plan")} {...size} />
      <Composition id="S5-Instruction" component={S5Instruction} durationInFrames={sceneFrames("s5_instruction")} {...size} />
      <Composition id="S6-Verify" component={S6Verify} durationInFrames={sceneFrames("s6_verify")} {...size} />
      <Composition id="S7-Aws" component={S7Aws} durationInFrames={sceneFrames("s7_aws")} {...size} />
      <Composition id="S8-Results" component={S8Results} durationInFrames={sceneFrames("s8_results")} {...size} />
      <Composition id="S9-Close" component={S9Close} durationInFrames={sceneFrames("s9_close")} {...size} />
    </Folder>
  </>
);
