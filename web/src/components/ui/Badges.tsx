import { useLang } from "../../i18n/lang";

export function SimBadge({ speed, simulated }: { speed: number; simulated: boolean }) {
  const { lang } = useLang();
  if (!simulated && speed <= 1) return null;
  const text =
    lang === "hi"
      ? speed > 1 ? `${speed}× तेज़ सिमुलेशन` : "सिमुलेशन"
      : speed > 1 ? `Simulated, ${speed}× speed` : "Simulated data";
  return (
    <span className="sim-badge" title="Simulated classroom; outdoor air is a real 2025 Delhi day">
      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M1 2l5 4-5 4zM6 2l5 4-5 4z" fill="currentColor" /></svg>
      {text}
    </span>
  );
}

export function AqiBadge({ aqi, category, en, hi }: { aqi: number; category: string; en: string; hi: string }) {
  const { lang } = useLang();
  return (
    <span className="aqi-badge num" data-cat={category}>
      <span>{lang === "hi" ? "बाहर" : "Outside"}</span>
      <span>AQI {aqi}</span>
      <span lang={lang}>{lang === "hi" ? hi : en}</span>
    </span>
  );
}
