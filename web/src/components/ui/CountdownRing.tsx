/** Time left on an instruction, as a ring that empties. */
export function CountdownRing({ remaining, total, label }: { remaining: number; total: number; label: string }) {
  const r = 30;
  const c = 2 * Math.PI * r;
  const frac = Math.max(0, Math.min(1, remaining / Math.max(total, 1)));
  const v = Math.max(0, Math.round(remaining));
  const text = `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`;
  return (
    <div className="ring" role="timer" aria-label={`${label}: ${text}`}>
      <svg width="76" height="76" viewBox="0 0 76 76" aria-hidden="true">
        <circle cx="38" cy="38" r={r} fill="none" stroke="var(--rule)" strokeWidth="6" />
        <circle cx="38" cy="38" r={r} fill="none" stroke="var(--haldi)" strokeWidth="6" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - frac)} transform="rotate(-90 38 38)"
          style={{ transition: "stroke-dashoffset 1s linear" }} />
      </svg>
      <span className="ring__text num">{text}</span>
    </div>
  );
}
