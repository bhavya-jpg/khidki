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
  return "hi";
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

export function LangToggle() {
  const { lang, setLang } = useLang();
  return (
    <button
      type="button"
      className="lang-toggle"
      onClick={() => setLang(lang === "hi" ? "en" : "hi")}
      aria-label={lang === "hi" ? "Switch to English" : "हिंदी में देखें"}
    >
      {lang === "hi" ? "English" : "हिंदी"}
    </button>
  );
}
