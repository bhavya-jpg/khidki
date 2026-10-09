import { useState } from "react";
import { AirWindow } from "../components/AirWindow/AirWindow";
import type { WindowState } from "../types";

const STATES: WindowState[] = ["closed", "cracked", "open_one", "open_both"];

/** Development page for the AirWindow: every input on a slider. */
export default function DevWindow() {
  const [outdoor, setOutdoor] = useState(240);
  const [indoor, setIndoor] = useState(150);
  const [co2, setCo2] = useState(1600);
  const [state, setState] = useState<WindowState>("closed");
  const [variant, setVariant] = useState<"hero" | "calm" | "mini" | "compare">("calm");
  const row = { display: "grid", gridTemplateColumns: "10rem 1fr 5rem", alignItems: "center", gap: 8 } as const;
  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px", display: "grid", gap: 24 }}>
      <h1 style={{ margin: 0 }}>AirWindow</h1>
      <div style={{ maxWidth: variant === "mini" ? 200 : 560 }}>
        <AirWindow outdoorPm={outdoor} indoorPm={indoor} co2={co2} window={state} variant={variant} />
      </div>
      <div style={{ display: "grid", gap: 12 }}>
        <label style={row}>Outdoor PM2.5<input type="range" min={0} max={500} value={outdoor} onChange={(e) => setOutdoor(+e.target.value)} /><span className="num">{outdoor}</span></label>
        <label style={row}>Indoor PM2.5<input type="range" min={0} max={500} value={indoor} onChange={(e) => setIndoor(+e.target.value)} /><span className="num">{indoor}</span></label>
        <label style={row}>CO₂ (ppm)<input type="range" min={400} max={4000} step={25} value={co2} onChange={(e) => setCo2(+e.target.value)} /><span className="num">{co2}</span></label>
        <label style={row}>Window
          <select value={state} onChange={(e) => setState(e.target.value as WindowState)}>{STATES.map((s) => <option key={s}>{s}</option>)}</select><span />
        </label>
        <label style={row}>Variant
          <select value={variant} onChange={(e) => setVariant(e.target.value as typeof variant)}>{["hero", "calm", "mini", "compare"].map((s) => <option key={s}>{s}</option>)}</select><span />
        </label>
      </div>
    </main>
  );
}
