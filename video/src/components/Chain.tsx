import { prog } from "../lib";
import { C } from "../theme";

/** The deployed Step Functions state machine's states, lit in the order an execution passes through them. */
export const Chain: React.FC<{ frame: number; from: number; over: number; states: string[]; notes?: Record<string, string> }> = ({ frame, from, over, states, notes = {} }) => (
  <div style={{ display: "flex", alignItems: "flex-start", gap: 0 }}>
    {states.map((s, i) => {
      const on = prog(frame, from + (i / states.length) * over, 10);
      return (
        <div key={s + i} style={{ display: "flex", alignItems: "flex-start" }}>
          {i > 0 && <div style={{ width: 34, height: 4, marginTop: 34, background: C.breath, opacity: on, scale: `${on} 1`, transformOrigin: "left center" }} />}
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                padding: "16px 22px", borderRadius: 14, fontSize: 28, fontWeight: 700, whiteSpace: "nowrap",
                background: on > 0.5 ? C.breathInk : C.raised, color: on > 0.5 ? C.chalk : C.ink3, border: `2px solid ${on > 0.5 ? C.breathInk : C.rule}`,
              }}
            >
              {s}
            </div>
            {notes[s] && <div style={{ marginTop: 8, fontSize: 24, color: C.ink2, opacity: on }}>{notes[s]}</div>}
          </div>
        </div>
      );
    })}
  </div>
);
