import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { AirWindow } from "../components/AirWindow/AirWindow";
import { WindowIcon } from "../components/ui/WindowIcon";
import { LangToggle, useLang } from "../i18n/lang";
import type { WindowState } from "../types";
import "./Landing.css";

/** Three states of one 44-child classroom with outdoor PM2.5 at 250 µg/m³, from Khidki's physics model
 *  (tests/test_physics.py): shut for a period, wide open, and what Khidki's plan holds. */
const SCENES: {
  key: string;
  window: WindowState;
  co2: number;
  pmIn: number;
  stretch: number;
  title: { en: string; hi: string };
  line: { en: string; hi: string };
}[] = [
  {
    key: "shut", window: "closed", co2: 2380, pmIn: 156, stretch: 75,
    title: { en: "Shut", hi: "बंद" },
    line: { en: "The children's breath pushes CO₂ past 2,000 ppm in one period.", hi: "एक ही पीरियड में बच्चों की साँस से CO₂ 2,000 ppm के पार।" },
  },
  {
    key: "open", window: "open_both", co2: 1030, pmIn: 242, stretch: 125,
    title: { en: "Open", hi: "खुली" },
    line: { en: "Fresh enough, but the room fills with 97% of the smog outside.", hi: "हवा ताज़ी, पर बाहर का 97% स्मॉग कमरे में।" },
  },
  {
    key: "khidki", window: "open_one", co2: 1380, pmIn: 214, stretch: 105,
    title: { en: "Khidki", hi: "खिड़की" },
    line: { en: "Open at the right minute, for the right time. Then check the air really changed.", hi: "सही मिनट पर, सही समय के लिए खोलें। फिर जाँचें कि हवा सच में बदली।" },
  },
];

interface Bench {
  rooms: Record<string, { days: number; policies: Record<string, { pm_pct_of_always_open: number; co2_min_over_1500: number; requests: number; cold_deg_min: number }> }>;
  paired: Record<string, { co2_better_days: number; days: number; median_pm_diff_pts: number }>;
}

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) {
      el.classList.add("is-in");
      return;
    }
    const io = new IntersectionObserver(([e]) => e.isIntersecting && (el.classList.add("is-in"), io.disconnect()), {
      threshold: 0.18,
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return ref;
}

function Reveal({ children, className = "", as: Tag = "section", id }: { children: ReactNode; className?: string; as?: "section" | "div"; id?: string }) {
  const ref = useReveal<HTMLElement>();
  return (
    <Tag ref={ref as never} id={id} className={`reveal ${className}`}>
      {children}
    </Tag>
  );
}

export default function Landing() {
  const { lang } = useLang();
  const t = (x: { en: string; hi: string }) => x[lang];
  const [scene, setScene] = useState(0);
  const [auto, setAuto] = useState(true);
  const [bench, setBench] = useState<Bench | null>(null);

  useEffect(() => {
    if (!auto || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = window.setInterval(() => setScene((s) => (s + 1) % SCENES.length), 4800);
    return () => window.clearInterval(id);
  }, [auto]);

  useEffect(() => {
    fetch("/benchmark.json").then((r) => r.json()).then(setBench).catch(() => setBench(null));
  }, []);

  const s = SCENES[scene];
  const nb = bench?.rooms.no_purifier;
  const k = nb?.policies.KHIDKI;
  const alarm = nb?.policies.CO2_ALARM;
  const pairedNb = bench?.paired.no_purifier;

  return (
    <div className="landing">
      <header className="nav">
        <Link to="/" className="nav__brand">
          <span lang="hi">खिड़की</span>
          <span className="nav__latin">Khidki</span>
        </Link>
        <nav className="nav__links" aria-label="Main">
          <a href="#how">{lang === "hi" ? "कैसे काम करता है" : "How it works"}</a>
          <a href="#results">{lang === "hi" ? "नतीजे" : "Results"}</a>
          <Link to="/teacher/6B">{lang === "hi" ? "शिक्षक स्क्रीन" : "Teacher screen"}</Link>
        </nav>
        <LangToggle />
      </header>

      {/* ── hero ── */}
      <section className="hero">
        <div className="hero__copy">
          <p className="hero__kicker">
            {lang === "hi" ? "दिल्ली की कक्षाओं के लिए, ख़राब हवा वाले दिनों में" : "For Delhi classrooms, on bad-air days"}
          </p>
          <h1 className="hero__title" style={{ fontStretch: `${s.stretch}%` }}>
            <span lang="hi">खिड़की खोलें,</span>
            <span lang="hi">या बंद रखें?</span>
          </h1>
          <p className="hero__sub">
            {lang === "hi"
              ? "Khidki शिक्षक को बताता है कि खिड़कियाँ ठीक किस मिनट खोलें और बंद करें, ताकि बच्चे कम धुआँ साँस में लें और CO₂ भी काबू में रहे। फिर CO₂ की रेखा से जाँचता है कि हवा सच में बदली।"
              : "Khidki tells a teacher the exact minute to open or close the classroom windows, so 40 children breathe less smog and stay below the CO₂ levels that wreck concentration. Then it checks, from the CO₂ curve, that the air really changed."}
          </p>
          <div className="hero__cta">
            <Link to="/teacher/6B" className="cta cta--primary">
              {lang === "hi" ? "शिक्षक की स्क्रीन देखें" : "See the teacher's screen"}
            </Link>
            <a href="#how" className="cta cta--ghost">
              {lang === "hi" ? "कैसे काम करता है" : "How it works"}
            </a>
          </div>
        </div>

        <figure className="hero__stage">
          <div className="hero__wall">
            <AirWindow outdoorPm={250} indoorPm={s.pmIn} co2={s.co2} window={s.window} variant="hero" showLegend={false} />
          </div>
          <div className="scenes" role="tablist" aria-label={lang === "hi" ? "तीन हालात" : "Three situations"}>
            {SCENES.map((x, i) => (
              <button
                key={x.key}
                role="tab"
                aria-selected={i === scene}
                className={`scene ${i === scene ? "is-on" : ""}`}
                onClick={() => {
                  setScene(i);
                  setAuto(false);
                }}
              >
                <WindowIcon state={x.window} size={20} />
                <span lang={lang}>{t(x.title)}</span>
              </button>
            ))}
          </div>
          <div className="hero__numbers">
            <div>
              <span className="hero__num num">{s.co2.toLocaleString("en-IN")}</span>
              <span className="hero__unit">ppm CO₂</span>
            </div>
            <div>
              <span className="hero__num num">{s.pmIn}</span>
              <span className="hero__unit">µg/m³ PM2.5 {lang === "hi" ? "अंदर" : "inside"}</span>
            </div>
          </div>
          <figcaption className="hero__caption">
            <span lang={lang}>{t(s.line)}</span>
            <small>
              {lang === "hi"
                ? "44 बच्चों की कक्षा, बाहर PM2.5 250 µg/m³। संख्याएँ Khidki के भौतिक मॉडल से। हर बिंदु ≈ 2 µg/m³ PM2.5।"
                : "A 44-child classroom with outdoor PM2.5 at 250 µg/m³. Numbers from Khidki's physics model. Each dot ≈ 2 µg/m³ of PM2.5."}
            </small>
          </figcaption>
        </figure>
      </section>

      {/* ── the dilemma, in numbers ── */}
      <Reveal className="facts">
        <div className="fact">
          <span className="fact__num num">+3,450</span>
          <span className="fact__unit">ppm/h</span>
          <p>{lang === "hi" ? "44 बच्चे हर घंटे इतना CO₂ जोड़ते हैं, एक 166 m³ कमरे में।" : "CO₂ that 44 children add every hour to a 166 m³ classroom."}</p>
        </div>
        <div className="fact">
          <span className="fact__num num">2,380</span>
          <span className="fact__unit">ppm</span>
          <p>{lang === "hi" ? "खिड़कियाँ बंद रहें तो एक 40 मिनट के पीरियड के बाद।" : "After one 40-minute period with the windows shut."}</p>
        </div>
        <div className="fact">
          <span className="fact__num num">97%</span>
          <span className="fact__unit">{lang === "hi" ? "बाहर का" : "of outside"}</span>
          <p>{lang === "hi" ? "खिड़कियाँ खुली रहें तो कमरे में इतना PM2.5।" : "The PM2.5 a wide-open room ends up with."}</p>
        </div>
        <div className="fact fact--quote">
          <p>
            {lang === "hi"
              ? "2025 के एक अध्ययन में CO₂ अलार्म ने कक्षा का CO₂ लगभग 19% घटाया, पर खिड़कियाँ खुलने से PM बढ़ गया।"
              : "In a 2025 classroom study, CO₂ alarms cut CO₂ by about 19%, but PM went up as the windows opened."}
          </p>
          <small>Rawat, Kumar et al., Science of the Total Environment 980 (2025)</small>
        </div>
      </Reveal>

      {/* ── how it works ── */}
      <Reveal className="how" id="how">
        <h2 className="section__title">{lang === "hi" ? "हर दिन, चार क़दम" : "Every day, four steps"}</h2>
        <div className="bento">
          <article className="tile tile--plan">
            <span className="tile__n num">01</span>
            <h3>{lang === "hi" ? "सुबह 6 बजे योजना" : "A plan at 6 AM"}</h3>
            <p>
              {lang === "hi"
                ? "पूर्वानुमान, टाइमटेबल और कमरे की भौतिकी से, हर 5 मिनट की योजना। स्कूल के नियम Cedar नीतियों में लिखे हैं: PM2.5 90 से ऊपर तो PT अंदर।"
                : "From the forecast, the timetable and each room's own physics, a plan in 5-minute steps. School rules are Cedar policies: PE moves indoors when forecast PM2.5 is above 90."}
            </p>
            <div className="mini-ribbon" aria-hidden="true">
              {Array.from({ length: 48 }, (_, i) => (
                <i key={i} className={`o${i < 8 ? 0 : i < 13 ? 2 : i < 22 ? 0 : i < 27 ? 3 : i < 36 ? 1 : i < 40 ? 3 : 0}`} />
              ))}
            </div>
          </article>
          <article className="tile tile--nudge">
            <span className="tile__n num">02</span>
            <h3>{lang === "hi" ? "एक शांत निर्देश" : "One calm instruction"}</h3>
            <p>{lang === "hi" ? "दिन में ज़्यादा से ज़्यादा 6 बार। हिंदी और अंग्रेज़ी में।" : "At most six a day, in Hindi and English."}</p>
            <div className="mini-card" aria-hidden="true">
              <WindowIcon state="open_both" size={22} />
              <span lang="hi">दोनों तरफ़ खोलिए</span>
              <b>4:00</b>
            </div>
          </article>
          <article className="tile tile--verify">
            <span className="tile__n num">03</span>
            <h3>{lang === "hi" ? "हवा से जाँच" : "Checked by the air"}</h3>
            <p>
              {lang === "hi"
                ? "बच्चों की साँस ही ट्रेसर गैस है। CO₂ कितनी तेज़ी से गिरता है, उससे पता चलता है कि खिड़की सच में खुली या बस एक तरफ़।"
                : "The children's own breath is the tracer gas. How fast CO₂ falls tells Khidki whether the window really opened, or only one side did."}
            </p>
            <svg className="mini-curve" viewBox="0 0 240 90" aria-hidden="true">
              <path d="M0 70 C40 60 70 35 100 22" fill="none" stroke="var(--haldi)" strokeWidth="3" strokeLinecap="round" />
              <path d="M100 22 C130 18 150 46 175 58 C195 66 215 70 240 71" fill="none" stroke="var(--breath)" strokeWidth="3" strokeLinecap="round" />
              <circle cx="100" cy="22" r="5" fill="var(--ink)" />
              <text x="106" y="14" fontSize="11" fill="var(--ink-2)">{lang === "hi" ? "खोल दीं" : "opened"}</text>
            </svg>
          </article>
          <article className="tile tile--replan">
            <span className="tile__n num">04</span>
            <h3>{lang === "hi" ? "हर 5 मिनट नई योजना" : "Re-planned every 5 minutes"}</h3>
            <p>{lang === "hi" ? "\"अभी नहीं हो सकता: ठंड\"? Khidki उसी के हिसाब से योजना बदल देता है।" : "\"Can't right now: too cold\"? Khidki plans around it."}</p>
            <div className="replan-demo" aria-hidden="true">
              {(lang === "hi" ? ["ठंड", "शोर", "बारिश", "परीक्षा"] : ["Too cold", "Too noisy", "Raining", "Exam on"]).map((c, i) => (
                <span key={c} className={i === 0 ? "is-picked" : ""}>{c}</span>
              ))}
              <svg width="28" height="16" viewBox="0 0 28 16"><path d="M2 8h22m-6-6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              <div className="mini-ribbon">
                {Array.from({ length: 24 }, (_, i) => <i key={i} className={`o${i < 6 ? 2 : i < 16 ? 1 : 0}`} />)}
              </div>
            </div>
          </article>
        </div>
      </Reveal>

      {/* ── results ── */}
      <Reveal className="results" id="results">
        <h2 className="section__title">{lang === "hi" ? "48 असली दिनों पर" : "Tested on 48 real days"}</h2>
        <p className="section__lead">
          {lang === "hi"
            ? "अक्टूबर से दिसंबर 2025 के दिल्ली के स्कूली दिनों की असली बाहरी हवा, एक सिम्युलेटेड कक्षा में। वही शिक्षक व्यवहार, CO₂ अलार्म से तुलना। यह फ़ील्ड ट्रायल नहीं है।"
            : "Real outdoor air from Delhi school days, October to December 2025, through a simulated classroom, against a CO₂ alarm with the same teacher behaviour. A simulation, not a field trial."}
        </p>
        {k && alarm && pairedNb ? (
          <div className="stats">
            <div className="stat stat--big">
              <span className="stat__num num">{Math.round((1 - k.co2_min_over_1500 / alarm.co2_min_over_1500) * 100)}%</span>
              <span className="stat__label">{lang === "hi" ? "कम घुटन वाले मिनट" : "fewer stuffy minutes"}</span>
              <p>
                {lang === "hi"
                  ? `1,500 ppm से ऊपर रोज़ ${Math.round(k.co2_min_over_1500)} मिनट, अलार्म के ${Math.round(alarm.co2_min_over_1500)} के मुक़ाबले। ${pairedNb.days} में से ${pairedNb.co2_better_days} दिन बेहतर।`
                  : `${Math.round(k.co2_min_over_1500)} minutes a day above 1,500 ppm, against the alarm's ${Math.round(alarm.co2_min_over_1500)}. Better on ${pairedNb.co2_better_days} of ${pairedNb.days} days.`}
              </p>
            </div>
            <div className="stat">
              <span className="stat__num num">{Math.round(k.requests)} <small>vs</small> {Math.round(alarm.requests)}</span>
              <span className="stat__label">{lang === "hi" ? "शिक्षक को रोज़ के अनुरोध" : "requests to the teacher a day"}</span>
            </div>
            <div className="stat stat--honest">
              <span className="stat__num num">+{pairedNb.median_pm_diff_pts}</span>
              <span className="stat__label">{lang === "hi" ? "अंक ज़्यादा PM2.5" : "points more PM2.5"}</span>
              <p>
                {lang === "hi"
                  ? "बिना प्यूरीफ़ायर के, 44 बच्चों को इतनी ताज़ी हवा चाहिए कि सिर्फ़ समय से धुआँ ज़्यादा नहीं घटता। हम यह खुलकर बताते हैं।"
                  : "Without a purifier, 44 children need so much fresh air that timing alone can't cut smog much. We say so."}
              </p>
            </div>
            <figure className="stat stat--chart">
              <img src="/benchmark-pareto.png" alt={lang === "hi" ? "Pareto चार्ट: Khidki बनाम CO₂ अलार्म" : "Pareto chart: Khidki against a CO₂ alarm and three other policies"} loading="lazy" />
            </figure>
          </div>
        ) : (
          <p className="section__lead">{lang === "hi" ? "नतीजे लोड हो रहे हैं…" : "Loading results…"}</p>
        )}
      </Reveal>

      {/* ── aws ── */}
      <Reveal className="aws">
        <h2 className="section__title">{lang === "hi" ? "AWS पर बना" : "Built on AWS"}</h2>
        <ul className="aws__list">
          {[
            ["Cedar", lang === "hi" ? "स्कूल के सुरक्षा नियम, कोड में" : "school safety rules as code"],
            ["Strands Agents", lang === "hi" ? "हिंदी में सवाल-जवाब, बिना गढ़े अंकों के" : "answers in Hindi with numbers it can't make up"],
            ["Amazon Bedrock", lang === "hi" ? "भाषा, फ़ैसले नहीं" : "language, never decisions"],
            ["AWS Step Functions", lang === "hi" ? "निर्देश, इंतज़ार, हवा से जाँच" : "nudge, wait, verify from the air"],
            ["AWS Lambda", lang === "hi" ? "योजना और API" : "planner and API"],
            ["Amazon DynamoDB", lang === "hi" ? "कमरे, योजनाएँ, रीडिंग" : "rooms, plans, readings"],
            ["Amazon EventBridge", lang === "hi" ? "सुबह 6 बजे की योजना" : "the 6 AM plan"],
            ["Amazon Polly", lang === "hi" ? "हिंदी आवाज़" : "Hindi voice"],
          ].map(([name, role]) => (
            <li key={name}>
              <b>{name}</b>
              <span>{role}</span>
            </li>
          ))}
        </ul>
      </Reveal>

      <footer className="foot">
        <p>
          {lang === "hi"
            ? "स्कूल और लोग काल्पनिक हैं। कक्षा के सेंसर सिम्युलेटेड हैं; बाहर की हवा असली है (CAMS, Open-Meteo के ज़रिए, CC BY 4.0)। Khidki कोई चिकित्सा उपकरण नहीं है।"
            : "The school and people are fictional. Classroom sensors are simulated; outdoor air is real (CAMS via Open-Meteo, CC BY 4.0). Khidki is not a medical device."}
        </p>
        <p>
          {lang === "hi" ? "Environmental Hacks 2026 के लिए बनाया। AI कोडिंग टूल: Claude Code।" : "Built for Environmental Hacks 2026. AI coding tool used: Claude Code."}
        </p>
      </footer>
    </div>
  );
}
