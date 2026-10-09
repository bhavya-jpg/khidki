import { useLang } from "../../i18n/lang";
import type { PlanStepView, WindowState } from "../../types";

const TIMETABLE = [
  { a: 450, b: 470, en: "Assembly", hi: "प्रार्थना" },
  { a: 470, b: 505, en: "1", hi: "1" }, { a: 505, b: 540, en: "2", hi: "2" },
  { a: 540, b: 575, en: "3", hi: "3" }, { a: 575, b: 610, en: "4", hi: "4" },
  { a: 610, b: 640, en: "Recess", hi: "रिसेस" },
  { a: 640, b: 675, en: "5", hi: "5" }, { a: 675, b: 710, en: "6", hi: "6" },
  { a: 710, b: 745, en: "7", hi: "7" }, { a: 745, b: 780, en: "8", hi: "8" },
];
const START = 420, END = 810;
export const OPENNESS: Record<WindowState, number> = { closed: 0, cracked: 1, open_one: 2, open_both: 3 };
const LEGEND: { s: WindowState; en: string; hi: string }[] = [
  { s: "closed", en: "Shut", hi: "बंद" },
  { s: "cracked", en: "A little open", hi: "थोड़ी खुली" },
  { s: "open_one", en: "One side", hi: "एक तरफ़" },
  { s: "open_both", en: "Both sides", hi: "दोनों तरफ़" },
];

/** The day's plan as one stripe per 5 minutes, darker = more open. Purifier time is marked underneath. */
export function AirRibbon({ steps, nowMin }: { steps: PlanStepView[]; nowMin: number }) {
  const { lang } = useLang();
  const pct = (m: number) => `${((m - START) / (END - START)) * 100}%`;
  return (
    <figure className="ribbon" aria-label={lang === "hi" ? "आज की खिड़की योजना" : "Today's window plan"}>
      <div className="ribbon__periods" aria-hidden="true">
        {TIMETABLE.map((p) => (
          <span key={p.a} style={{ left: pct(p.a), width: `calc(${pct(p.b)} - ${pct(p.a)})` }}
            className={p.en.length > 1 ? "is-break" : ""}>{lang === "hi" ? p.hi : p.en}</span>
        ))}
      </div>
      <div className="ribbon__track">
        {steps.map((s) => (
          <span key={s.t_min} className={`ribbon__cell o${OPENNESS[s.window]} ${s.t_min + 5 <= nowMin ? "is-past" : ""}`}
            style={{ left: pct(s.t_min), width: `calc(${pct(s.t_min + 5)} - ${pct(s.t_min)} + 0.5px)` }}
            title={`${s.t} ${s.window}${s.purifier === "on" ? " + purifier" : ""}`} />
        ))}
        {steps.filter((s) => s.purifier === "on").map((s) => (
          <span key={`p${s.t_min}`} className="ribbon__purifier"
            style={{ left: pct(s.t_min), width: `calc(${pct(s.t_min + 5)} - ${pct(s.t_min)})` }} />
        ))}
        {nowMin >= START && nowMin <= END && <span className="ribbon__now" style={{ left: pct(nowMin) }} />}
      </div>
      <div className="ribbon__axis num" aria-hidden="true">
        {[420, 480, 540, 600, 660, 720, 780].map((m) => (
          <span key={m} style={{ left: pct(m) }}>{`${String(Math.floor(m / 60)).padStart(2, "0")}:00`}</span>
        ))}
      </div>
      <figcaption className="ribbon__legend">
        {LEGEND.map((l) => (
          <span key={l.s}><i className={`swatch o${OPENNESS[l.s]}`} />{lang === "hi" ? l.hi : l.en}</span>
        ))}
        {steps.some((s) => s.purifier === "on") && (
          <span><i className="swatch swatch--purifier" />{lang === "hi" ? "प्यूरीफ़ायर" : "Purifier"}</span>
        )}
      </figcaption>
    </figure>
  );
}
