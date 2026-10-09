import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, usePoll } from "../api";
import { AirWindow } from "../components/AirWindow/AirWindow";
import { AqiBadge, SimBadge } from "../components/ui/Badges";
import { Sparkline } from "../components/ui/Sparkline";
import { WindowIcon } from "../components/ui/WindowIcon";
import { Bi, LangToggle, useLang } from "../i18n/lang";
import type { ActionCard, Bilingual, RoomNow, WindowState } from "../types";
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
  verified: { en: "Air is changing ✓", hi: "हवा बदल रही है ✓" },
  cant: { en: "Can't right now", hi: "अभी नहीं हो सकता" },
  why: { en: "Why can't you?", hi: "क्यों नहीं हो सकता?" },
  noted: { en: "Noted. Khidki will plan around it.", hi: "ठीक है। Khidki इसके हिसाब से योजना बदलेगा।" },
};

function mmss(s: number) {
  const v = Math.max(0, Math.round(s));
  return `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`;
}

export default function Teacher() {
  const { roomId = "6B" } = useParams();
  const { data, error, lastOk, refresh } = usePoll<RoomNow>(`/v1/rooms/${roomId}/now`, 2000);
  const { lang } = useLang();
  const [showCant, setShowCant] = useState(false);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<Bilingual | null>(null);
  const seenOutcome = useRef<string | null>(null);

  // The one orchestrated moment: when verification lands, say so for a few seconds.
  useEffect(() => {
    const o = data?.last_outcome;
    if (!o?.nudge_id || seenOutcome.current === o.nudge_id) return;
    const first = seenOutcome.current === null;
    seenOutcome.current = o.nudge_id;
    if (first) return;
    if (o.status === "verified" || o.status === "verified_silent") {
      setFlash(T.verified);
      const id = window.setTimeout(() => setFlash(null), 3000);
      return () => window.clearTimeout(id);
    }
  }, [data?.last_outcome]);

  async function ack(card: ActionCard, result: "done" | "cant", reason?: string) {
    setBusy(true);
    try {
      await api.post(`/v1/nudges/${card.nudge_id}/ack`, { result, reason });
      if (result === "cant") setFlash(T.noted);
      setShowCant(false);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!data) {
    return (
      <main className="teacher teacher--loading">
        <p>{error ? `Can't reach Khidki: ${error}` : lang === "hi" ? "लोड हो रहा है…" : "Loading…"}</p>
      </main>
    );
  }

  const offlineFor = lastOk && error ? (Date.now() - lastOk) / 60000 : 0;
  const stale = (data.indoor.stale_s ?? 0) > 240;
  const card = data.card;
  const target: WindowState = card.kind === "action" ? card.action.window : data.window.believed.window;
  const shown: WindowState = data.window.inferred;
  const co2Series = data.series.map((s) => s.co2);
  const pmSeries = data.series.map((s) => s.pm25 ?? NaN);
  const rising = co2Series.length > 3 && co2Series[co2Series.length - 1] > co2Series[co2Series.length - 4] + 20;

  return (
    <main className={`teacher ${offlineFor > 0.5 ? "teacher--offline" : ""}`}>
      <header className="teacher__bar">
        <h1 className="teacher__room">
          <span lang="hi">कक्षा {data.room_id}</span>
          <span className="visually-hidden"> (Class {data.room_id})</span>
        </h1>
        <AqiBadge aqi={data.outdoor.aqi} category={data.outdoor.category} en={data.outdoor.category_en} hi={data.outdoor.category_hi} />
        <span className="teacher__clock num">{data.clock.time}</span>
        <SimBadge speed={data.clock.speed} simulated={data.simulated} />
        <LangToggle />
      </header>

      <section className="teacher__window">
        <AirWindow
          outdoorPm={data.outdoor.pm25}
          indoorPm={data.indoor.pm25}
          co2={data.indoor.co2}
          window={shown}
          purifier={data.window.believed.purifier === "on"}
          framePaint={data.frame_paint}
          variant="calm"
          rising={rising}
        />
        {stale && (
          <p className="teacher__note" role="status">
            {lang === "hi"
              ? `सेंसर से ${Math.round((data.indoor.stale_s ?? 0) / 60)} मिनट से कोई रीडिंग नहीं। लाइव हवा के बिना योजना दिखा रहे हैं।`
              : `No reading from the sensor for ${Math.round((data.indoor.stale_s ?? 0) / 60)} minutes. Showing the plan without live air data.`}
          </p>
        )}
      </section>

      <section className="teacher__decision" aria-live="polite">
        {flash ? (
          <p className="teacher__flash"><Bi t={flash} /></p>
        ) : card.kind === "keep" ? (
          <div className="keep">
            <p className="keep__line">
              <WindowIcon state={data.window.believed.window} size={28} />
              <Bi t={card.text} />
            </p>
            {card.next && (
              <p className="keep__next num">
                {lang === "hi" ? `अगला बदलाव ${card.next.t} पर: ` : `Next change at ${card.next.t}: `}
                <span lang={lang}>{card.next.text[lang]}</span>
              </p>
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

      <footer className="teacher__foot">
        <Sparkline values={co2Series} label="CO₂" unit="ppm" color="var(--haldi-ink)" />
        <Sparkline values={pmSeries} label="PM2.5" unit="µg/m³" color="var(--ink-2)" />
        {offlineFor > 0.5 && (
          <p className="teacher__note" role="status">
            {lang === "hi"
              ? `${Math.round(offlineFor)} मिनट से कनेक्शन नहीं। आख़िरी निर्देश दिखा रहे हैं।`
              : `No connection for ${Math.round(offlineFor)} min. Last instruction shown.`}
          </p>
        )}
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
      {card.follow_up_text && card.status === "follow_up" ? (
        <p className="action__followup"><Bi t={card.follow_up_text} /></p>
      ) : null}
      <h2 className="action__verb" style={{ fontStretch: `${stretch}%` }}>
        <Bi t={card.text} />
      </h2>
      <p className="action__duration num">
        <span lang={lang}>{lang === "hi" ? `${card.duration_min} मिनट के लिए` : `For ${card.duration_min} minutes`}</span>
        <span className="action__countdown" aria-label={lang === "hi" ? "बचा समय" : "Time left"}>{mmss(remaining)}</span>
      </p>
      <p className="action__why"><span lang={lang}>{card.reason[lang]}</span></p>
      {card.status === "verifying" ? (
        <p className="action__checking"><Bi t={T.checking} /></p>
      ) : waiting ? (
        <div className="action__buttons">
          <button type="button" className="btn btn--primary" onClick={props.onDone} disabled={busy}>
            <Bi t={card.button} />
          </button>
          <button type="button" className="btn btn--secondary" onClick={props.onCant} disabled={busy} aria-expanded={showCant}>
            <Bi t={T.cant} />
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
