import { useCallback, useEffect, useRef, useState } from "react";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body.message ?? detail; // local mode says `detail`, the cloud says `message`
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body: unknown, headers?: Record<string, string>) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body), headers }),
};

/** Poll a GET endpoint. Keeps the last good value when a request fails, and reports how long since it worked. */
export function usePoll<T>(path: string, everyMs = 2000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastOk, setLastOk] = useState<number | null>(null);
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const d = await api.get<T>(path);
      if (!alive.current) return;
      setData(d);
      setError(null);
      setLastOk(Date.now());
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : String(e));
    }
  }, [path]);

  useEffect(() => {
    alive.current = true;
    void refresh();
    const id = window.setInterval(() => void refresh(), everyMs);
    return () => {
      alive.current = false;
      window.clearInterval(id);
    };
  }, [refresh, everyMs]);

  return { data, error, lastOk, refresh };
}

/**
 * Keep the live demo's classroom moving while this page is open and visible. The deployed API advances its
 * simulated rooms on each pulse; local mode has its own simulator and answers "local". Returns the demo's
 * state: null until the first answer (a fresh morning takes a few seconds to prepare, and the pages wait
 * for it instead of showing the previous visitor's leftovers), then "running", "resting" (the monthly
 * free-tier cap was reached), "external", "local", or "off" when there is no autopilot to wait for.
 */
export function usePulse(everyMs = 3000) {
  const [state, setState] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    let off = false;
    const settle = (s: string) => {
      if (alive) setState((prev) => (s === "off" && prev !== null ? prev : s));
    };
    const giveUp = window.setTimeout(() => settle("off"), 25000); // never keep a page waiting on the demo
    const beat = async () => {
      if (off || document.hidden) return;
      try {
        const res = await fetch("/v1/sim/pulse", { method: "POST" });
        if (res.status === 404 || res.status === 405) {
          off = true;
          settle("off");
          return;
        }
        if (!res.ok) {
          settle("off");
          return;
        }
        const body = (await res.json()) as { state?: string };
        if (alive) setState(body.state ?? "off");
        if (body.state === "local") off = true;
      } catch {
        settle("off"); // offline: the page's own offline banner covers it
      }
    };
    void beat();
    const id = window.setInterval(() => void beat(), everyMs);
    return () => {
      alive = false;
      window.clearInterval(id);
      window.clearTimeout(giveUp);
    };
  }, [everyMs]);
  return state;
}
