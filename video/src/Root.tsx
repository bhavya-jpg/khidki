import { Composition, Folder } from "remotion";
import { Explainer } from "./Explainer";
import { FPS, sceneFrames, totalFrames } from "./lib";
import { S1Question } from "./scenes/S1Question";
import { S2Dilemma } from "./scenes/S2Dilemma";
import { S3Khidki } from "./scenes/S3Khidki";
import { S4Decide } from "./scenes/S4Decide";
import { S4bRules } from "./scenes/S4bRules";
import { S5Instruction } from "./scenes/S5Instruction";
import { S6Verify } from "./scenes/S6Verify";
import { S7Arch } from "./scenes/S7Arch";
import { S7bStack } from "./scenes/S7bStack";
import { S8Results } from "./scenes/S8Results";
import { S9Built } from "./scenes/S9Built";
import { S10Close } from "./scenes/S10Close";

const size = { width: 1920, height: 1080, fps: FPS } as const;

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Khidki"
      component={Explainer}
      durationInFrames={totalFrames()}
      {...size}
    />
    <Folder name="Scenes">
      <Composition
        id="S1-Question"
        component={S1Question}
        durationInFrames={sceneFrames("s1_question")}
        {...size}
      />
      <Composition
        id="S2-Dilemma"
        component={S2Dilemma}
        durationInFrames={sceneFrames("s2_dilemma")}
        {...size}
      />
      <Composition
        id="S3-Khidki"
        component={S3Khidki}
        durationInFrames={sceneFrames("s3_khidki")}
        {...size}
      />
      <Composition
        id="S4-Decide"
        component={S4Decide}
        durationInFrames={sceneFrames("s4_decide")}
        {...size}
      />
      <Composition
        id="S4b-Rules"
        component={S4bRules}
        durationInFrames={sceneFrames("s4b_rules")}
        {...size}
      />
      <Composition
        id="S5-Instruction"
        component={S5Instruction}
        durationInFrames={sceneFrames("s5_instruction")}
        {...size}
      />
      <Composition
        id="S6-Verify"
        component={S6Verify}
        durationInFrames={sceneFrames("s6_verify")}
        {...size}
      />
      <Composition
        id="S7-Arch"
        component={S7Arch}
        durationInFrames={sceneFrames("s7_arch")}
        {...size}
      />
      <Composition
        id="S7b-Stack"
        component={S7bStack}
        durationInFrames={sceneFrames("s7b_stack")}
        {...size}
      />
      <Composition
        id="S8-Results"
        component={S8Results}
        durationInFrames={sceneFrames("s8_results")}
        {...size}
      />
      <Composition
        id="S9-Built"
        component={S9Built}
        durationInFrames={sceneFrames("s9_built")}
        {...size}
      />
      <Composition
        id="S10-Close"
        component={S10Close}
        durationInFrames={sceneFrames("s10_close")}
        {...size}
      />
    </Folder>
  </>
);
