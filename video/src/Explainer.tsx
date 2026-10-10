import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { useVideoConfig } from "remotion";
import { sceneFrames, TRANSITION } from "./lib";
import { S1Question } from "./scenes/S1Question";
import { S2Dilemma } from "./scenes/S2Dilemma";
import { S3Khidki } from "./scenes/S3Khidki";
import { S4Plan } from "./scenes/S4Plan";
import { S5Instruction } from "./scenes/S5Instruction";
import { S6Verify } from "./scenes/S6Verify";
import { S7Aws } from "./scenes/S7Aws";
import { S8Results } from "./scenes/S8Results";
import { S9Close } from "./scenes/S9Close";

const cut = <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: TRANSITION })} />;

/** Khidki in under three minutes. Each scene is as long as its narration (src/data/vo.json). */
export const Explainer: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence name="1 The question" durationInFrames={sceneFrames("s1_question")} premountFor={fps}>
        <S1Question />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="2 The dilemma" durationInFrames={sceneFrames("s2_dilemma")} premountFor={fps}>
        <S2Dilemma />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="3 Khidki" durationInFrames={sceneFrames("s3_khidki")} premountFor={fps}>
        <S3Khidki />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="4 The 6 AM plan" durationInFrames={sceneFrames("s4_plan")} premountFor={fps}>
        <S4Plan />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="5 One instruction" durationInFrames={sceneFrames("s5_instruction")} premountFor={fps}>
        <S5Instruction />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="6 Verified from the air" durationInFrames={sceneFrames("s6_verify")} premountFor={fps}>
        <S6Verify />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="7 Built on AWS" durationInFrames={sceneFrames("s7_aws")} premountFor={fps}>
        <S7Aws />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="8 Results" durationInFrames={sceneFrames("s8_results")} premountFor={fps}>
        <S8Results />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence name="9 Close" durationInFrames={sceneFrames("s9_close")} premountFor={fps}>
        <S9Close />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
