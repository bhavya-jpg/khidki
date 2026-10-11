import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, usePoll, usePulse } from "../api";
import { AirWindow, WindowPlaceholder } from "../components/AirWindow/AirWindow";
import { AirRibbon } from "../components/ui/AirRibbon";
import { SimBadge } from "../components/ui/Badges";
import { CountdownRing } from "../components/ui/CountdownRing";
import { co2Status } from "../components/ui/co2";
import { Readout } from "../components/ui/Readout";
import { WindowIcon } from "../components/ui/WindowIcon";
import { Bi, LangToggle, useLang } from "../i18n/lang";
import type { ActionCard, Bilingual, PlanView, RoomNow, WindowState } from "../types";
import "./Teacher.css";

const STRETCH: Record<WindowState, number> = { closed: 75, cracked: 90, open_one: 110, open_both: 125 };

const CANT: { key: string; t: Bilingual }[] = [
  { key: "cold", t: { en: "Too cold", hi: "ठंड" } },
  { key: "noise", t: { en: "Too noisy", hi: "शोर" } },
  { key: "rain", t: { en: "Raining", hi: "बारिश" } },
  { key: "exam", t: { en: "Exam on", hi: "परीक्षा" } },
];

const T = {
  checking: { en: "Done. Checking the air…", hi: "हो गया। हवा जाँच रहे हैं…" },
  checkingSub: { en: "Khidki is reading the CO₂ curve to confirm.", hi: "Khidki CO₂ की रेखा पढ़कर पक्का कर रहा है।" },
  verified: { en: "Air is changing ✓", hi: "हवा बदल रही है ✓" },
  verifiedSub: { en: "Confirmed from the CO₂ curve.", hi: "CO₂ की रेखा से पक्का हुआ।" },
  cant: { en: "Can't right now", hi: "अभी नहीं हो सकता" },
  why: { en: "What's stopping you?", hi: "क्या दिक़्क़त है?" },
  noted: { en: "Noted. Khidki will plan around it.", hi: "ठीक है। Khidki इसके हिसाब से योजना बदलेगा।" },
  notedSub: { en: "No need to do anything else.", hi: "आपको और कुछ नहीं करना है।" },
  nowLabel: { en: "Now", hi: "अभी" },
  todayPlan: { en: "Today's plan", hi: "आज की योजना" },
  stripe: { en: "One stripe = 5 minutes", hi: "एक पट्टी = 5 मिनट" },
};

export default function Teacher() {
  const { roomId = "6B" } = useParams();
  const { data, error, lastOk, refresh } = usePoll<RoomNow>(`/v1/rooms/${roomId}/now`, 2000);
  const plan = usePoll<PlanView>(`/v1/rooms/${roomId}/plan`, 15000);
  const { lang } = useLang();
  const pulse = usePulse();
  const [showCant, setShowCant] = useState(false);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<{ t: Bilingual; sub: Bilingual } | null>(null);
  const seenOutcome = useRef<string | null>(null);

  // The one orchestrated moment: when verification lands, say so for a few seconds.
  // Whatever outcome was already there when the page opened is not news; anything after that is.
  const loaded = data !== null;
  const outcomeId = data?.last_outcome?.nudge_id ?? "";
  const outcomeStatus = data?.last_outcome?.status ?? null;
  useEffect(() => {
    if (!loaded) return;
    if (seenOutcome.current === null) {
      seenOutcome.current = outcomeId;
      return;
    }
    if (!outcomeId || seenOutcome.current === outcomeId) return;
    seenOutcome.current = outcomeId;
    if (outcomeStatus === "verified" || outcomeStatus === "verified_silent") {
      setFlash({ t: T.verified, sub: T.verifiedSub });
      window.setTimeout(() => setFlash(null), 3500);
    }
  }, [loaded, outcomeId, outcomeStatus]);

  async function ack(card: ActionCard, result: "done" | "cant", reason?: string) {
    setBusy(true);
    try {
      await api.post(`/v1/nudges/${card.nudge_id}/ack`, { result, reason });
      if (result === "cant") {
        setFlash({ t: T.noted, sub: T.notedSub });
        window.setTimeout(() => setFlash(null), 3500);
      }
      setShowCant(false);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!data || pulse === null) {
    return (
      <main className="teacher teacher--loading">
        <div className="teacher__wait">
          <figure className="air-window air-window--calm">
            <div className="air-window__box">
              <WindowPlaceholder />
            </div>
          </figure>
          <p role="status" lang={lang}>
            {error
              ? lang === "hi"
                ? `Khidki तक पहुँच नहीं हो रही: ${error}`
                : `Can't reach Khidki: ${error}`
              : lang === "hi"
                ? "कक्षा खुल रही है… एक नई सुबह शुरू हो रही है।"
                : "Opening the classroom… a fresh school morning is starting."}
          </p>
        </div>
      </main>
    );
  }

  const offlineFor = lastOk && error ? (Date.now() - lastOk) / 60000 : 0;
  const stale = (data.indoor.stale_s ?? 0) > 240;
  const card = data.card;
  const target: WindowState = card.kind === "action" ? card.action.window : data.window.believed.window;
  const co2Series = data.series.map((s) => s.co2);
  const rising = co2Series.length > 3 && co2Series[co2Series.length - 1] > co2Series[co2Series.length - 4] + 20;
  const falling = co2Series.length > 3 && co2Series[co2Series.length - 1] < co2Series[co2Series.length - 4] - 20;
  const co2 = co2Status(data.indoor.co2);
  const [hh, mm] = data.clock.time.split(":").map(Number);
  const nowMin = hh * 60 + mm;
  const outTone = data.outdoor.aqi > 300 ? "bad" : data.outdoor.aqi > 200 ? "warn" : "good";
  // An instruction is waiting for the teacher: the window itself carries the signal, readable from across
  // the room without reading (docs/design-refs/NOTES.md, principle 2).
  const due = data.card.kind === "action" && (data.card.status === "issued" || data.card.status === "follow_up");

  return (
    <main className={`teacher ${offlineFor > 0.5 ? "teacher--offline" : ""}`}>
      <header className="teacher__bar">
        <div className="teacher__id">
          <span className="teacher__brand" lang="hi">खिड़की</span>
          <h1 className="teacher__room">
            <span lang={lang}>{lang === "hi" ? `कक्षा ${data.room_id}` : `Class ${data.room_id}`}</span>
          </h1>
        </div>
        <span className="teacher__clock num">{data.clock.time}</span>
        <SimBadge speed={data.clock.speed} simulated={data.simulated} />
        <LangToggle />
      </header>

      {pulse === "resting" && (
        <p className="demo-note" role="status" lang={lang} style={{ gridColumn: "1 / -1" }}>
          {lang === "hi"
            ? "लाइव कक्षा अभी रुकी है, ताकि AWS के मुफ़्त दायरे में रहे। वीडियो देखिए या लैपटॉप पर चलाइए।"
            : "The live classroom is resting to stay inside the AWS free tier. Watch the video, or run it on a laptop."}
        </p>
      )}
      <section className="teacher__stage" data-due={due ? "true" : undefined}>
        <div className="wall">
          <AirWindow
            outdoorPm={data.outdoor.pm25}
            indoorPm={data.indoor.pm25}
            co2={data.indoor.co2}
            window={data.window.inferred}
            purifier={data.window.believed.purifier === "on"}
            framePaint={data.frame_paint}
            variant="calm"
            rising={rising}
          />
        </div>
        <div className="readouts">
          <Readout label="CO₂" value={data.indoor.co2.toLocaleString("en-IN")} unit="ppm" tone={co2.tone}
            trend={rising ? "up" : falling ? "down" : "flat"} status={<span lang={lang}>{co2.t[lang]}</span>} />
          <Readout label={lang === "hi" ? "अंदर PM2.5" : "PM2.5 inside"}
            value={data.indoor.pm25 == null ? "–" : String(Math.round(data.indoor.pm25))} unit="µg/m³" />
          <Readout label={lang === "hi" ? "बाहर AQI" : "AQI outside"} value={String(data.outdoor.aqi)} unit=""
            tone={outTone} status={<span lang={lang}>{lang === "hi" ? data.outdoor.category_hi : data.outdoor.category_en}</span>} />
        </div>
        {stale && (
          <p className="teacher__note" role="status">
            {lang === "hi"
              ? `सेंसर से ${Math.round((data.indoor.stale_s ?? 0) / 60)} मिनट से कोई रीडिंग नहीं। लाइव हवा के बिना योजना दिखा रहे हैं।`
              : `No reading from the sensor for ${Math.round((data.indoor.stale_s ?? 0) / 60)} minutes. Showing the plan without live air data.`}
          </p>
        )}
      </section>

      <section className={`panel ${card.kind === "action" ? "panel--action" : ""}`} aria-live="polite">
        {flash ? (
          <div className="flash">
            <p className="flash__title"><Bi t={flash.t} secondary={false} /></p>
            <p className="flash__sub"><span lang={lang}>{flash.sub[lang]}</span></p>
          </div>
        ) : card.kind === "keep" ? (
          <div className="keep">
            <span className="panel__eyebrow"><span lang={lang}>{T.nowLabel[lang]}</span></span>
            <p className="keep__line">
              <WindowIcon state={data.window.believed.window} size={36} />
              <Bi t={card.text} />
            </p>
            {card.next && (
              <div className="keep__next">
                <span className="keep__time num">{card.next.t}</span>
                <span>
                  <WindowIcon state={card.next.action.window} size={22} />
                  <span lang={lang}>{card.next.text[lang]}</span>
                </span>
              </div>
            )}
          </div>
        ) : (
          <ActionPanel
            card={card}
            nowSim={data.clock.now}
            stretch={STRETCH[target]}
            busy={busy}
            showCant={showCant}
            onDone={() => void ack(card, "done")}
            onCant={() => setShowCant((v) => !v)}
            onReason={(r) => void ack(card, "cant", r)}
          />
        )}
      </section>

      <footer className="teacher__day">
        <div className="teacher__dayhead">
          <span lang={lang}>
            {T.todayPlan[lang]}
            <span className="teacher__unit">{T.stripe[lang]}</span>
          </span>
          {offlineFor <= 0.5 && data.requests && (
            <span className="teacher__budget num" lang={lang}>
              {lang === "hi"
                ? `आज के अनुरोध: ${data.requests.max} में से ${data.requests.used}`
                : `${data.requests.used} of ${data.requests.max} requests used today`}
            </span>
          )}
          {offlineFor > 0.5 && (
            <span className="teacher__note" role="status">
              {lang === "hi"
                ? `${Math.round(offlineFor)} मिनट से कनेक्शन नहीं। आख़िरी निर्देश दिखा रहे हैं।`
                : `No connection for ${Math.round(offlineFor)} min. Last instruction shown.`}
            </span>
          )}
        </div>
        {plan.data && <AirRibbon steps={plan.data.day_steps ?? plan.data.steps} nowMin={nowMin} />}
      </footer>
    </main>
  );
}

function ActionPanel(props: {
  card: ActionCard;
  nowSim: number;
  stretch: number;
  busy: boolean;
  showCant: boolean;
  onDone: () => void;
  onCant: () => void;
  onReason: (r: string) => void;
}) {
  const { card, nowSim, stretch, busy, showCant } = props;
  const { lang } = useLang();
  const remaining = card.issued_at + card.duration_min * 60 - nowSim;
  const waiting = card.status === "issued" || card.status === "follow_up";
  return (
    <div className="action">
      {card.follow_up_text && card.status === "follow_up" && (
        <p className="action__followup">
          <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l10 18H2z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /><path d="M12 10v5M12 18v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
          <Bi t={card.follow_up_text} />
        </p>
      )}
      <div className="action__head">
        <span className="action__icon"><WindowIcon state={card.action.window} size={44} /></span>
        <CountdownRing remaining={remaining} total={card.duration_min * 60} label={lang === "hi" ? "बचा समय" : "Time left"} />
      </div>
      <h2 className="action__verb" style={{ fontStretch: `${stretch}%` }}>
        <Bi t={card.text} />
      </h2>
      <p className="action__meta">
        <span className="num" lang={lang}>{lang === "hi" ? `${card.duration_min} मिनट के लिए` : `For ${card.duration_min} minutes`}</span>
        <span className="action__why" lang={lang}>{card.reason[lang]}</span>
      </p>
      {card.status === "verifying" ? (
        <div className="action__checking">
          <span className="pulse" aria-hidden="true" />
          <span><Bi t={T.checking} secondary={false} /><small lang={lang}>{T.checkingSub[lang]}</small></span>
        </div>
      ) : waiting ? (
        <div className="action__buttons">
          <button type="button" className="btn btn--secondary" onClick={props.onCant} disabled={busy} aria-expanded={showCant}>
            <Bi t={T.cant} />
          </button>
          <button type="button" className="btn btn--primary" onClick={props.onDone} disabled={busy}>
            <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12.5l5 5L20 6.5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
            <Bi t={card.button} />
          </button>
        </div>
      ) : null}
      {showCant && waiting && (
        <div className="action__reasons" role="group" aria-label={T.why[lang]}>
          {CANT.map((c) => (
            <button key={c.key} type="button" className="chip" onClick={() => props.onReason(c.key)} disabled={busy}>
              <Bi t={c.t} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
