import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, usePoll, usePulse } from "../api";
import { AirWindow } from "../components/AirWindow/AirWindow";
import { SimBadge } from "../components/ui/Badges";
import { co2Status } from "../components/ui/co2";
import { WindowIcon } from "../components/ui/WindowIcon";
import { LangToggle, useLang } from "../i18n/lang";
import type { AuditEntry, Decision, SchoolRoom, SchoolToday } from "../types";
import "./School.css";

const PASS_KEY = "khidki.principal"; // this browser tab only

const WINDOW_WORD = {
  en: { closed: "Shut", cracked: "A little open", open_one: "One side open", open_both: "Both sides open" },
  hi: { closed: "बंद", cracked: "थोड़ी खुली", open_one: "एक तरफ़ खुली", open_both: "दोनों तरफ़ खुली" },
} as const;

export default function School() {
  const pulse = usePulse(); // keeps the live demo's classroom moving while this page is open
  const { schoolId = "dsv" } = useParams();
  const { data, error, refresh } = usePoll<SchoolToday>(`/v1/schools/${schoolId}/today`, 4000);
  const audit = usePoll<AuditEntry[]>(`/v1/schools/${schoolId}/audit`, 15000);
  const { lang } = useLang();

  if (!data || pulse === null) {
    return (
      <main className="school school--loading">
        <p role="status" lang={lang}>
          {error ? `Can't reach Khidki: ${error}` : lang === "hi" ? "स्कूल खुल रहा है…" : "Opening the school…"}
        </p>
      </main>
    );
  }
  const severe = data.grap_stage >= 3;
  const [hh, mm] = data.clock.time.split(":").map(Number);
  const outdoorNow = interpOutdoor(data.hourly, hh + mm / 60);
  return (
    <main className="school">
      <header className="school__bar">
        <div>
          <span className="school__brand" lang="hi">खिड़की</span>
          <h1>{data.name}</h1>
        </div>
        <span className="school__date num"><span>{data.date}</span><b>{data.clock.time}</b></span>
        <SimBadge speed={data.clock.speed} simulated={data.simulated} />
        <LangToggle />
      </header>

      <section className={`grap ${severe ? "grap--severe" : ""}`} aria-label="GRAP">
        <div className="grap__stage">
          <span className="grap__label">{lang === "hi" ? "संकेतक GRAP चरण" : "Indicative GRAP stage"}</span>
          <span className="grap__value" lang={lang}>{lang === "hi" ? data.grap.name_hi : data.grap.name_en}</span>
          <span className="grap__aqi num">{lang === "hi" ? "शहर AQI" : "City AQI"} {data.city_aqi}</span>
        </div>
        <p className="grap__note" lang={lang}>
          {(lang === "hi" ? data.grap.reminder_hi : data.grap.reminder_en) ||
            (lang === "hi" ? "आधिकारिक चरण वही है जो CAQM ने घोषित किया है।" : "The official stage is whatever CAQM has ordered.")}{" "}
          <a href={data.grap.circulars_url} target="_blank" rel="noreferrer">{lang === "hi" ? "DoE परिपत्र" : "DoE circulars"}</a>
        </p>
      </section>

      <div className="school__grid">
        <section className="panel-s rooms" aria-labelledby="rooms-h">
          <h2 id="rooms-h">{lang === "hi" ? "कक्षाएँ, अभी" : "Classrooms, now"}</h2>
          <ul>
            {data.rooms.map((r) => <RoomRow key={r.room_id} room={r} outdoorPm={outdoorNow} />)}
          </ul>
        </section>

        <section className="panel-s decisions" aria-labelledby="dec-h">
          <h2 id="dec-h">{lang === "hi" ? "आज के फ़ैसले" : "Today's decisions"}</h2>
          <p className="muted">
            {lang === "hi"
              ? "बाहर की गतिविधियाँ Cedar नीतियों से तय होती हैं। प्रधानाचार्य कारण लिखकर बदल सकते हैं; हर बदलाव दर्ज होता है।"
              : "Outdoor activities are decided by Cedar policies. The principal can override with a reason; every override is logged."}
          </p>
          <ul>
            {data.decisions.map((d) => (
              <DecisionRow key={d.key} d={d} policies={data.policies} schoolId={schoolId} onDone={() => { void refresh(); void audit.refresh(); }} />
            ))}
          </ul>
        </section>

        <section className="panel-s forecast" aria-labelledby="fc-h">
          <h2 id="fc-h">{lang === "hi" ? "बाहर PM2.5, आज" : "Outdoor PM2.5 today"}</h2>
          <ForecastChart hourly={data.hourly} />
          <p className="muted small">{data.forecast_source}. CAMS via Open-Meteo, CC BY 4.0.</p>
        </section>

        <section className="panel-s audit" aria-labelledby="au-h">
          <h2 id="au-h">{lang === "hi" ? "बदलावों का रिकॉर्ड" : "Override log"}</h2>
          {audit.data && audit.data.length > 0 ? (
            <ul>
              {audit.data.map((a) => (
                <li key={`${a.at}${a.key}`}>
                  <span className="num">{a.time}</span>
                  <span lang={lang}>
                    {lang === "hi"
                      ? <><b>{a.label}</b> को {a.outdoor ? "बाहर" : "अंदर"} किया गया, क्योंकि {a.reason}</>
                      : <><b>{a.label}</b> {a.outdoor ? "held outdoors" : "moved indoors"} because {a.reason}</>}
                  </span>
                  <span className="muted">{a.by}{a.policy_ids.length > 0 ? `, ${lang === "hi" ? "नीति" : "over policy"} ${a.policy_ids.join(", ")}` : ""}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">{lang === "hi" ? "आज कोई बदलाव नहीं।" : "No overrides today."}</p>
          )}
        </section>
      </div>
      <footer className="school__foot muted small">
        {lang === "hi"
          ? "स्कूल काल्पनिक है। कक्षा के सेंसर सिम्युलेटेड हैं; बाहर की हवा असली है। Khidki कोई चिकित्सा उपकरण नहीं है।"
          : "The school is fictional. Classroom sensors are simulated; outdoor air is real. Khidki is not a medical device."}
      </footer>
    </main>
  );
}

function interpOutdoor(hourly: SchoolToday["hourly"], hour: number): number {
  const pts = hourly.hour_min.map((m, i) => [m / 60, hourly.pm25[i]] as const).filter((p) => p[1] != null) as [number, number][];
  if (!pts.length) return 0;
  for (let i = 1; i < pts.length; i++) {
    if (pts[i][0] >= hour) {
      const [h0, v0] = pts[i - 1], [h1, v1] = pts[i];
      return v0 + ((v1 - v0) * (hour - h0)) / (h1 - h0 || 1);
    }
  }
  return pts[pts.length - 1][1];
}

function RoomRow({ room, outdoorPm }: { room: SchoolRoom; outdoorPm: number }) {
  const { lang } = useLang();
  const action = room.card.kind === "action";
  const verified = room.last_outcome?.status === "verified" || room.last_outcome?.status === "verified_silent";
  const air = co2Status(room.indoor.co2);
  return (
    <li className={`room ${action ? "room--action" : ""}`}>
      <div className="room__win">
        <AirWindow outdoorPm={outdoorPm} indoorPm={room.indoor.pm25} co2={room.indoor.co2} window={room.window.inferred}
          framePaint={room.frame_paint} variant="mini" showLegend={false} />
      </div>
      <div className="room__body">
        <div className="room__head">
          <Link to={`/teacher/${room.room_id}`} className="room__name">{room.name}</Link>
          {room.has_purifier && <span className="tag">{lang === "hi" ? "प्यूरीफ़ायर" : "Purifier"}</span>}
        </div>
        <div className="room__nums num">
          <span>
            <b>{room.indoor.co2.toLocaleString("en-IN")}</b> ppm CO₂,{" "}
            <span className={`room__word room__word--${air.tone}`} lang={lang}>{lang === "hi" ? air.t.hi : air.t.en.toLowerCase()}</span>
          </span>
          <span><b>{room.indoor.pm25 == null ? "–" : Math.round(room.indoor.pm25)}</b> µg/m³ PM2.5</span>
        </div>
        <div className="room__state">
          <WindowIcon state={room.window.inferred} size={18} />
          <span lang={lang}>{WINDOW_WORD[lang][room.window.inferred]}</span>
          {action ? (
            <span className="status status--action" lang={lang}>{lang === "hi" ? "निर्देश चल रहा है" : "Instruction out"}</span>
          ) : verified ? (
            <span className="status status--ok" lang={lang}>✓ {lang === "hi" ? "हवा से पक्का" : "Verified from the air"}</span>
          ) : (
            <span className="status" lang={lang}>{lang === "hi" ? "कोई निर्देश बाक़ी नहीं" : "No instruction out"}</span>
          )}
        </div>
        {action && room.card.kind === "action" && <p className="room__instr" lang={lang}>{room.card.text[lang]}</p>}
      </div>
    </li>
  );
}

function DecisionRow({ d, policies, schoolId, onDone }: { d: Decision; policies: SchoolToday["policies"]; schoolId: string; onDone: () => void }) {
  const { lang } = useLang();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [needPass, setNeedPass] = useState(false);
  const [pass, setPass] = useState(() => {
    try {
      return sessionStorage.getItem(PASS_KEY) ?? "";
    } catch {
      return "";
    }
  });
  const outdoor = d.override ?? d.outdoor;
  const fired = d.policy_ids.filter((p) => p.startsWith("S"));
  async function submit() {
    setErr(null);
    try {
      // The deployed API asks for the principal passcode; local mode has no login and ignores the header.
      const headers = pass ? { "x-khidki-admin": pass } : undefined;
      await api.post(`/v1/schools/${schoolId}/override`, { key: d.key, outdoor: !outdoor, reason }, headers);
      try {
        if (pass) sessionStorage.setItem(PASS_KEY, pass);
      } catch {
        /* storage blocked: ask again next time */
      }
      setOpen(false);
      setReason("");
      setNeedPass(false);
      onDone();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setNeedPass(true);
        setErr(lang === "hi" ? "प्रिंसिपल का पासकोड चाहिए।" : "This needs the principal's passcode.");
      } else {
        setErr(e instanceof Error ? e.message : String(e));
      }
    }
  }
  return (
    <li className="decision">
      <div className="decision__main">
        <span className="decision__label">{d.label}</span>
        <span className="num muted">{d.start}–{d.end}</span>
        <span className={`chip-s ${outdoor ? "chip-s--out" : "chip-s--in"}`}>
          {outdoor ? (lang === "hi" ? "बाहर" : "Outdoors") : (lang === "hi" ? "अंदर" : "Indoors")}
        </span>
      </div>
      <p className="decision__why">
        {fired.length > 0 ? (
          <>
            <b>{fired.join(", ")}</b>{" "}
            <span lang={lang}>{fired.map((p) => policies[p]?.[lang]).filter(Boolean).join(" ")}</span>{" "}
            <span className="num">({lang === "hi" ? "पूर्वानुमान" : "forecast"} {d.max_pm25} µg/m³)</span>
          </>
        ) : (
          <span>{lang === "hi" ? "कोई नियम नहीं रोकता" : "No policy blocks it"} <span className="num">({d.max_pm25} µg/m³)</span></span>
        )}
      </p>
      {d.override !== null && d.override !== undefined && (
        <p className="decision__override">{lang === "hi" ? "बदला गया" : "Overridden"} {d.override_at}: “{d.override_reason}”</p>
      )}
      {open ? (
        <div className="decision__form">
          {/* The form reads as the sentence that will be logged. */}
          <label className="decision__sentence" lang={lang}>
            <span>
              {lang === "hi"
                ? <><b>{d.label}</b> को <b>{outdoor ? "अंदर" : "बाहर"}</b> करें, क्योंकि</>
                : <>{outdoor ? "Move" : "Hold"} <b>{d.label}</b> <b>{outdoor ? "indoors" : "outdoors"}</b> because</>}
            </span>
            <input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={200}
              aria-label={lang === "hi" ? "कारण (दर्ज होगा)" : "Reason (logged)"}
              placeholder={lang === "hi" ? "अंतर-स्कूल मैच है, मास्क दिए गए" : "there is an inter-school match, masks given"} />
          </label>
          {needPass && (
            <label className="decision__pass" lang={lang}>
              <span>{lang === "hi" ? "प्रिंसिपल का पासकोड" : "Principal's passcode"}</span>
              <input type="password" autoComplete="off" value={pass} onChange={(e) => setPass(e.target.value)} />
            </label>
          )}
          <p className="decision__note" lang={lang}>
            {lang === "hi" ? "यह वाक्य समय और नीति के साथ रिकॉर्ड में दर्ज होगा।" : "This sentence is logged with the time and the policy it overrides."}
          </p>
          <div className="decision__btns">
            <button type="button" className="btn-s btn-s--primary" disabled={reason.trim().length < 3 || (needPass && !pass)} onClick={() => void submit()}>
              {lang === "hi" ? "दर्ज करें" : "Log it"}
            </button>
            <button type="button" className="btn-s" onClick={() => setOpen(false)}>{lang === "hi" ? "रद्द" : "Cancel"}</button>
          </div>
          {err && <p className="err" role="alert">{err}</p>}
        </div>
      ) : (
        <button type="button" className="link-btn" onClick={() => setOpen(true)}>{lang === "hi" ? "बदलें" : "Override"}</button>
      )}
    </li>
  );
}

function ForecastChart({ hourly }: { hourly: SchoolToday["hourly"] }) {
  const { lang } = useLang();
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const pts = hourly.hour_min.map((m, i) => ({ h: m / 60, v: hourly.pm25[i] })).filter((p) => p.v != null) as { h: number; v: number }[];
  if (!pts.length) return null;
  const W = 640, H = 220, L = 40, R = 12, T = 12, B = 28;
  const maxV = Math.max(120, ...pts.map((p) => p.v)) * 1.1;
  const x = (h: number) => L + (h / 24) * (W - L - R);
  const y = (v: number) => T + (1 - v / maxV) * (H - T - B);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(p.h).toFixed(1)},${y(p.v).toFixed(1)}`).join("");
  const area = `${line}L${x(pts[pts.length - 1].h)},${y(0)}L${x(pts[0].h)},${y(0)}Z`;
  const ticks = [0, 50, 100, 150, 200, 250, 300].filter((t) => t < maxV);
  const hp = hover != null ? pts.reduce((a, b) => (Math.abs(b.h - hover) < Math.abs(a.h - hover) ? b : a)) : null;
  if (table) {
    return (
      <div>
        <button type="button" className="link-btn" onClick={() => setTable(false)}>{lang === "hi" ? "चार्ट दिखाएँ" : "Show as chart"}</button>
        <table className="fc-table num"><thead><tr><th>{lang === "hi" ? "समय" : "Hour"}</th><th>PM2.5 (µg/m³)</th></tr></thead>
          <tbody>{pts.map((p) => <tr key={p.h}><td>{String(p.h).padStart(2, "0")}:00</td><td>{Math.round(p.v)}</td></tr>)}</tbody></table>
      </div>
    );
  }
  return (
    <div className="fc">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={lang === "hi" ? "आज का बाहरी PM2.5 पूर्वानुमान, हर घंटे" : "Today's hourly outdoor PM2.5 forecast"}
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => { const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect(); setHover((((e.clientX - r.left) / r.width) * W - L) / (W - L - R) * 24); }}>
        <rect x={x(7.5)} y={T} width={x(13) - x(7.5)} height={H - T - B} fill="var(--rule)" opacity="0.45" />
        <text x={x(7.5) + 6} y={T + 14} fontSize="13" fill="var(--ink-2)">{lang === "hi" ? "स्कूल का समय" : "School hours"}</text>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="var(--rule)" strokeWidth="1" />
            <text x={L - 6} y={y(t) + 4} fontSize="13" textAnchor="end" fill="var(--ink-2)">{t}</text>
          </g>
        ))}
        <line x1={L} x2={W - R} y1={y(90)} y2={y(90)} stroke="var(--haldi-ink)" strokeDasharray="5 4" strokeWidth="1.5" />
        <text x={W - R} y={y(90) - 6} fontSize="13" textAnchor="end" fill="var(--haldi-ink)">{lang === "hi" ? "S2 सीमा 90" : "S2 limit 90"}</text>
        <path d={area} fill="var(--haze)" opacity="0.28" />
        <path d={line} fill="none" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" />
        {[0, 6, 12, 18, 24].map((h) => <text key={h} x={x(h)} y={H - 8} fontSize="13" textAnchor={h === 0 ? "start" : h === 24 ? "end" : "middle"} fill="var(--ink-2)">{String(h % 24).padStart(2, "0")}:00</text>)}
        {hp && (
          <g>
            <line x1={x(hp.h)} x2={x(hp.h)} y1={T} y2={H - B} stroke="var(--ink-3)" />
            <circle cx={x(hp.h)} cy={y(hp.v)} r="5" fill="var(--ink)" stroke="var(--raised)" strokeWidth="2" />
            <text x={Math.min(x(hp.h) + 8, W - 90)} y={Math.max(y(hp.v) - 10, T + 12)} fontSize="13" fill="var(--ink)" fontWeight="700">
              {String(hp.h).padStart(2, "0")}:00, {Math.round(hp.v)} µg/m³
            </text>
          </g>
        )}
      </svg>
      <button type="button" className="link-btn" onClick={() => setTable(true)}>{lang === "hi" ? "तालिका देखें" : "Show as table"}</button>
    </div>
  );
}
