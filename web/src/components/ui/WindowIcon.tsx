import type { WindowState } from "../../types";

/** Custom window-state icons, drawn at the stroke weight of Anek medium (1.75 px at 24 px). */
export function WindowIcon({ state, size = 24, title }: { state: WindowState; size?: number; title?: string }) {
  const left = state === "closed" ? "M4 4h8v16H4z" : state === "cracked" ? "M4 4l6 1.5v13L4 20z" : "M4 4l3 1.5v13L4 20z";
  const right = state === "open_both" ? "M20 4l-3 1.5v13L20 20z" : "M12 4h8v16h-8z";
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75}
      strokeLinejoin="round" role={title ? "img" : undefined} aria-hidden={title ? undefined : true}>
      {title && <title>{title}</title>}
      <path d="M3 3h18v18H3z" opacity={0.45} />
      <path d={left} />
      <path d={right} />
    </svg>
  );
}
