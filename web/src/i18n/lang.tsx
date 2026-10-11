import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Bilingual } from "../types";

export type Lang = "hi" | "en";
const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({ lang: "hi", setLang: () => {} });

function initial(): Lang {
  try {
    const saved = localStorage.getItem("khidki.lang");
    if (saved === "hi" || saved === "en") return saved;
  } catch {
    /* storage blocked */
  }
  // Teachers and parents are Hindi-first; the landing page's readers (judges, principals) start in English.
  return location.pathname.startsWith("/teacher") || location.pathname.startsWith("/parent") ? "hi" : "en";
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(initial);
  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem("khidki.lang", lang);
    } catch {
      /* storage blocked */
    }
  }, [lang]);
  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);

/** Primary text in the chosen language, with the other language as a quieter second line. */
export function Bi({ t, className, secondary = true }: { t: Bilingual; className?: string; secondary?: boolean }) {
  const { lang } = useLang();
  const other: Lang = lang === "hi" ? "en" : "hi";
  return (
    <span className={className}>
      <span lang={lang} className="bi-primary">
        {t[lang]}
      </span>
      {secondary && (
        <span lang={other} className="bi-secondary">
          {t[other]}
        </span>
      )}
    </span>
  );
}

/** Both languages are always visible and the current one is filled, so it is clear which one you are in. */
export function LangToggle() {
  const { lang, setLang } = useLang();
  return (
    <div className="lang-toggle" role="group" aria-label="Language / भाषा">
      <button type="button" lang="hi" className={lang === "hi" ? "is-on" : ""} aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>
        हिंदी
      </button>
      <button type="button" lang="en" className={lang === "en" ? "is-on" : ""} aria-pressed={lang === "en"} onClick={() => setLang("en")}>
        English
      </button>
    </div>
  );
}
