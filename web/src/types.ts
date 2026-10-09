// Mirrors the JSON returned by khidki_services.engine views. Kept in sync by tests/test_web_contract.py.

export type WindowState = "closed" | "cracked" | "open_one" | "open_both";
export type PurifierState = "off" | "on";
export type Bilingual = { en: string; hi: string };
export type ActionJson = { window: WindowState; purifier: PurifierState };

export interface ClockView {
  now: number;
  time: string;
  date: string;
  mode: "live" | "demo";
  speed: number;
  simulated: boolean;
}

export interface ActionCard {
  kind: "action";
  nudge_id: string;
  action: ActionJson;
  from: ActionJson;
  text: Bilingual;
  button: Bilingual;
  reason: Bilingual;
  reason_code: string;
  duration_min: number;
  status: "issued" | "verifying" | "follow_up" | "done";
  follow_up: "other_side" | "not_changed" | "gentle" | null;
  follow_up_text: Bilingual | null;
  issued_at: number;
  deadline: number;
  acked_at: number | null;
}

export interface KeepCard {
  kind: "keep";
  text: Bilingual;
  next: { t: string; action: ActionJson; text: Bilingual; reason_code: string } | null;
}

export interface RoomNow {
  room_id: string;
  name: string;
  grade: number;
  has_purifier: boolean;
  students: number;
  frame_paint: string;
  clock: ClockView;
  occupied: boolean;
  outdoor: {
    pm25: number;
    aqi: number;
    category: string;
    category_en: string;
    category_hi: string;
    temp: number;
    source: string;
  };
  indoor: { co2: number; pm25: number | null; last_ingest: number | null; stale_s: number | null };
  window: { believed: ActionJson; inferred: WindowState; confidence: number; implied_lam: number | null };
  card: ActionCard | KeepCard;
  last_outcome: { status: string | null; at: number; nudge_id: string } | null;
  series: { t: string; ts: number; co2: number; pm25: number | null }[];
  simulated: boolean;
}

export interface PlanStepView {
  t_min: number;
  t: string;
  window: WindowState;
  purifier: PurifierState;
  predicted_co2: number;
  predicted_pm: number;
  occupied: boolean;
  reason_code: string;
}

export interface PlanView {
  room_id: string;
  date: string;
  version: number;
  steps: PlanStepView[];
  instructions: { t_start: string; t_start_min: number; t_end_min: number; duration_min: number; action: ActionJson; reason_code: string }[];
  made_at: number;
  day_steps: PlanStepView[];
}
