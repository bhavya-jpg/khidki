import { useEffect, useMemo, useRef, useState } from "react";
import type { WindowState } from "../../types";
import { useLang } from "../../i18n/lang";
import { describe, useEncoding } from "./encoding";
import { AirWindowRenderer } from "./renderer";
import "./AirWindow.css";

export interface AirWindowProps {
  outdoorPm: number;
  indoorPm: number | null;
  co2: number;
  window: WindowState;
  purifier?: boolean;
  framePaint?: string;
  variant?: "hero" | "calm" | "mini" | "compare";
  rising?: boolean;
  simulated?: boolean;
  showLegend?: boolean;
  className?: string;
}

const VARIANT_OPTS = {
  hero: { fpsCap: 60, freezeAfterMs: 60_000 },
  compare: { fpsCap: 30, freezeAfterMs: 60_000 },
  calm: { fpsCap: 30, freezeAfterMs: 8_000 }, // battery and attention friendly
  mini: { fpsCap: 20, freezeAfterMs: 3_000 },
} as const;

function usePrefersReducedMotion() {
  const q = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() => typeof matchMedia !== "undefined" && matchMedia(q).matches);
  useEffect(() => {
    const m = matchMedia(q);
    const on = () => setReduced(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return reduced;
}

/** A plain window shape, shown at once so the space never looks empty while the data and the drawing load. */
export function WindowPlaceholder() {
  return (
    <div className="air-window__ph" aria-hidden="true">
      <i />
      <i />
    </div>
  );
}

/**
 * A classroom window whose contents are the air. Dots are PM2.5 (one dot = the page's shared µg/m³ value;
 * behind the glass is outside air, in front is the room), the warm haze is CO₂, and the panes really open.
 */
export function AirWindow({
  outdoorPm,
  indoorPm,
  co2,
  window: state,
  purifier = false,
  framePaint = "green",
  variant = "calm",
  rising,
  showLegend = true,
  className,
}: AirWindowProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<AirWindowRenderer | null>(null);
  const { pmPerParticle, setPmPerParticle } = useEncoding();
  const { lang } = useLang();
  const reduced = usePrefersReducedMotion();
  const [painted, setPainted] = useState(false);
  const air = useMemo(
    () => ({ outdoorPm, indoorPm, co2, window: state, purifier, pmPerParticle, framePaint }),
    [outdoorPm, indoorPm, co2, state, purifier, pmPerParticle, framePaint],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    const box = boxRef.current;
    if (!canvas || !box) return;
    const r = new AirWindowRenderer(canvas, air, VARIANT_OPTS[variant]);
    r.reducedMotion = reduced;
    // Adaptive quality: halve the particle budget for every window on the page together.
    r.onSlow = () => setPmPerParticle(Math.min(pmPerParticle * 2, 16));
    rendererRef.current = r;
    const ro = new ResizeObserver(([entry]) => r.resize(entry.contentRect.width, entry.contentRect.height));
    ro.observe(box);
    const scheme = matchMedia("(prefers-color-scheme: dark)");
    const onScheme = () => r.refreshPalette();
    scheme.addEventListener("change", onScheme);
    r.start();
    // The drawn window replaces the placeholder once it has had two frames to paint.
    const first = requestAnimationFrame(() => requestAnimationFrame(() => setPainted(true)));
    return () => {
      cancelAnimationFrame(first);
      ro.disconnect();
      scheme.removeEventListener("change", onScheme);
      r.stop();
      rendererRef.current = null;
    };
    // The renderer lives as long as the variant; data changes go through update().
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [variant]);

  useEffect(() => {
    const r = rendererRef.current;
    if (!r) return;
    r.reducedMotion = reduced;
    r.update(air);
  }, [air, reduced]);

  const label = describe(state, outdoorPm, indoorPm, co2, lang, rising);
  return (
    <figure className={`air-window air-window--${variant} ${className ?? ""}`}>
      <div ref={boxRef} className="air-window__box">
        {!painted && <WindowPlaceholder />}
        <canvas ref={canvasRef} role="img" aria-label={label} />
      </div>
      {showLegend && (
        <figcaption className="air-window__legend">
          {lang === "hi" ? (
            <span lang="hi">हर बिंदु ≈ {pmPerParticle} µg/m³ PM2.5। काँच के पीछे बाहर की हवा है, आगे कमरे की। पीली धुंध CO₂ है।</span>
          ) : (
            <span lang="en">Each dot ≈ {pmPerParticle} µg/m³ of PM2.5. Behind the glass: outside. In front: the room. Warm haze: CO₂.</span>
          )}
        </figcaption>
      )}
    </figure>
  );
}
