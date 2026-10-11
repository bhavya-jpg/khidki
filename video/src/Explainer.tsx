import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { useVideoConfig } from "remotion";
import { sceneFrames, TRANSITION } from "./lib";
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

const cut = (
  <TransitionSeries.Transition
    presentation={fade()}
    timing={linearTiming({ durationInFrames: TRANSITION })}
  />
);

/**
 * Khidki in under three minutes: what it does and who it helps, how it decides and checks without extra
 * hardware, what it is built with, the results, and what exists today. Each scene is as long as its
 * narration (src/data/vo.json).
 */
export const Explainer: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence
        name="1 The question"
        durationInFrames={sceneFrames("s1_question")}
        premountFor={fps}
      >
        <S1Question />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="2 The dilemma"
        durationInFrames={sceneFrames("s2_dilemma")}
        premountFor={fps}
      >
        <S2Dilemma />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="3 What Khidki does"
        durationInFrames={sceneFrames("s3_khidki")}
        premountFor={fps}
      >
        <S3Khidki />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="4 Deciding, with no hardware"
        durationInFrames={sceneFrames("s4_decide")}
        premountFor={fps}
      >
        <S4Decide />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="5 The rules, as Cedar policies"
        durationInFrames={sceneFrames("s4b_rules")}
        premountFor={fps}
      >
        <S4bRules />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="6 One instruction"
        durationInFrames={sceneFrames("s5_instruction")}
        premountFor={fps}
      >
        <S5Instruction />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="7 Checked from the air"
        durationInFrames={sceneFrames("s6_verify")}
        premountFor={fps}
      >
        <S6Verify />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="8 How it is built on AWS"
        durationInFrames={sceneFrames("s7_arch")}
        premountFor={fps}
      >
        <S7Arch />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="9 Under the hood"
        durationInFrames={sceneFrames("s7b_stack")}
        premountFor={fps}
      >
        <S7bStack />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="10 Results"
        durationInFrames={sceneFrames("s8_results")}
        premountFor={fps}
      >
        <S8Results />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="11 What we built"
        durationInFrames={sceneFrames("s9_built")}
        premountFor={fps}
      >
        <S9Built />
      </TransitionSeries.Sequence>
      {cut}
      <TransitionSeries.Sequence
        name="12 Close"
        durationInFrames={sceneFrames("s10_close")}
        premountFor={fps}
      >
        <S10Close />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
