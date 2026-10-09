/** A tiny line for the last hour. Values and labels in ink; the line in the given colour. */
export function Sparkline({ values, label, unit, color, width = 160, height = 36 }: {
  values: number[]; label: string; unit: string; color: string; width?: number; height?: number;
}) {
  const v = values.filter((x) => Number.isFinite(x));
  if (v.length < 2) return null;
  const lo = Math.min(...v), hi = Math.max(...v);
  const span = hi - lo || 1;
  const pts = v.map((x, i) => `${(i / (v.length - 1)) * (width - 4) + 2},${height - 2 - ((x - lo) / span) * (height - 4)}`).join(" ");
  const last = v[v.length - 1];
  return (
    <div className="sparkline">
      <svg width={width} height={height} role="img" aria-label={`${label}: ${Math.round(last)} ${unit}, last hour`}>
        <polyline points={pts} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <span className="sparkline__label num">{label} {Math.round(last).toLocaleString("en-IN")} {unit}</span>
    </div>
  );
}
