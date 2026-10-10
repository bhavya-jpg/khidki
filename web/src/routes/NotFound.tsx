import { Link } from "react-router-dom";
import { LangToggle, useLang } from "../i18n/lang";
import "./NotFound.css";

/** Any address we don't know: say so, and offer the four real screens. */
export default function NotFound() {
  const { lang } = useLang();
  const hi = lang === "hi";
  return (
    <main className="notfound">
      <header className="notfound__bar">
        <Link to="/" className="notfound__brand" lang="hi">खिड़की</Link>
        <LangToggle />
      </header>
      <h1 lang={lang}>{hi ? "यह पेज नहीं मिला" : "This page doesn't exist"}</h1>
      <p lang={lang}>{hi ? "पता जाँच लीजिए, या इनमें से कोई स्क्रीन खोलिए।" : "Check the address, or open one of these screens."}</p>
      <ul className="notfound__list">
        <li><Link to="/" lang={lang}>{hi ? "Khidki क्या है" : "What Khidki is"}</Link></li>
        <li><Link to="/teacher/6B" lang={lang}>{hi ? "शिक्षक की स्क्रीन (कक्षा 6B)" : "The teacher's screen (Class 6B)"}</Link></li>
        <li><Link to="/school/dsv" lang={lang}>{hi ? "प्रिंसिपल का पेज" : "The principal's page"}</Link></li>
        <li><Link to="/print/6B" lang={lang}>{hi ? "आज की समय-सारणी (प्रिंट)" : "Today's printable timetable"}</Link></li>
      </ul>
    </main>
  );
}
