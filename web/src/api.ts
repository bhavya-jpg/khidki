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
