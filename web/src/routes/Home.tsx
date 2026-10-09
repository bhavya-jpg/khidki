import { Link } from "react-router-dom";
import { LangToggle, useLang } from "../i18n/lang";

/** Placeholder until the scroll-scrubbed landing page (Phase 5). */
export default function Home() {
  const { lang } = useLang();
  return (
    <main style={{ maxWidth: 680, margin: "0 auto", padding: "48px 16px" }}>
      <p style={{ display: "flex", justifyContent: "flex-end" }}><LangToggle /></p>
      <h1 style={{ fontSize: "var(--step-5)", lineHeight: 1.05, margin: 0, fontWeight: 800 }}>
        <span lang="hi">खिड़की खोलें, या बंद रखें?</span>
      </h1>
      <p style={{ fontSize: "var(--step-1)", color: "var(--ink-2)" }}>
        {lang === "hi"
          ? "Khidki दिल्ली के ख़राब हवा वाले दिनों में शिक्षक को बताता है कि कक्षा की खिड़कियाँ कब खोलें और कब बंद करें।"
          : "Khidki tells a Delhi teacher exactly when to open or close the classroom windows on a bad-air day."}
      </p>
      <ul>
        <li><Link to="/teacher/6B">{lang === "hi" ? "कक्षा 6B का टैबलेट" : "Class 6B tablet"}</Link></li>
        <li><Link to="/teacher/3A">{lang === "hi" ? "कक्षा 3A का टैबलेट (प्यूरीफ़ायर वाला कमरा)" : "Class 3A tablet (room with a purifier)"}</Link></li>
        <li><Link to="/dev/window">AirWindow</Link></li>
      </ul>
      <p style={{ fontSize: "var(--step--1)", color: "var(--ink-3)" }}>
        Fictional school and people. Simulated classroom sensors; outdoor air is real (CAMS via Open-Meteo, CC BY 4.0).
        Not a medical device.
      </p>
    </main>
  );
}
