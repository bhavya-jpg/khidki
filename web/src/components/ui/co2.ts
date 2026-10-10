import type { Bilingual } from "../../types";

/** The plain word for a CO₂ reading, shared by the teacher and principal pages so a number never stands alone. */
export function co2Status(co2: number): { tone: "good" | "warn" | "bad"; t: Bilingual } {
  if (co2 < 1000) return { tone: "good", t: { en: "Fresh", hi: "ताज़ी" } };
  if (co2 < 1500) return { tone: "warn", t: { en: "Getting stuffy", hi: "भारी हो रही है" } };
  return { tone: "bad", t: { en: "Stuffy", hi: "घुटन वाली" } };
}
