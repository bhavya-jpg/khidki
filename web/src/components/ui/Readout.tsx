import type { ReactNode } from "react";

/** A big live number with its unit and a status word (never colour alone). */
export function Readout({ label, value, unit, status, tone = "neutral", trend, children }: {
  label: ReactNode;
  value: string;
  unit: string;
  status?: ReactNode;
  tone?: "good" | "warn" | "bad" | "neutral";
  trend?: "up" | "down" | "flat";
  children?: ReactNode;
}) {
  return (
    <div className={`readout readout--${tone}`}>
      <div className="readout__label">{label}</div>
      <div className="readout__value num">
        {value}
        <span className="readout__unit">{unit}</span>
        {trend && trend !== "flat" && (
          <svg className="readout__trend" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <path d={trend === "up" ? "M9 3l6 7h-4v5H7v-5H3z" : "M9 15l6-7h-4V3H7v5H3z"} fill="currentColor" />
          </svg>
        )}
      </div>
      {status && <div className="readout__status">{status}</div>}
      {children}
    </div>
  );
}
