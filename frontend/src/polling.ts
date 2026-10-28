import { useMemo, useSyncExternalStore } from "react";
import { api, ApiError } from "./client";

const configured = Number(import.meta.env.VITE_POLL_INTERVAL_MS || 30000);
export const pollInterval = Number.isFinite(configured)
  ? Math.max(5000, Math.min(configured, 300000))
  : 30000;
type Snapshot<T> = {
  status: number | null;
  data: T | null;
  error: string;
  loading: boolean;
  retrievedAt: string | null;
};
const entries = new Map<string, Entry<unknown>>();
const empty: Snapshot<never> = {
  status: null,
  data: null,
  error: "",
  loading: false,
  retrievedAt: null,
};
class Entry<T> {
  state: Snapshot<T> = {
    status: null,
    data: null,
    error: "",
    loading: true,
    retrievedAt: null,
  };
  listeners = new Set<() => void>();
  timer: ReturnType<typeof setTimeout> | undefined;
  controller: AbortController | undefined;
  failures = 0;
  running: Promise<void> | null = null;
  constructor(readonly path: string) {}
  emit(next: Snapshot<T>) {
    this.state = next;
    this.listeners.forEach((fn) => fn());
  }
  refresh = () => {
    if (this.running) return this.running;
    clearTimeout(this.timer);
    if (!navigator.onLine) {
      this.emit({
        ...this.state,
        loading: false,
        error:
          "ইন্টারনেট সংযোগ নেই; আগের তথ্য থাকলে পুরোনো হিসেবে দেখানো হচ্ছে।",
      });
      return Promise.resolve();
    }
    const c = new AbortController();
    this.controller = c;
    this.emit({ ...this.state, loading: !this.state.data });
    this.running = api<T>(this.path, { signal: c.signal })
      .then((data) => {
        if (!c.signal.aborted) {
          this.failures = 0;
          this.emit({
            data,
            status: null,
            error: "",
            loading: false,
            retrievedAt: new Date().toISOString(),
          });
        }
      })
      .catch((e) => {
        if (!c.signal.aborted) {
          this.failures++;
          this.emit({
            ...this.state,
            loading: false,
            error: (e as Error).message,
            status: e instanceof ApiError ? e.status : null,
          });
        }
      })
      .finally(() => {
        if (this.controller !== c) return;
        this.running = null;
        if (
          this.listeners.size &&
          !c.signal.aborted &&
          !document.hidden &&
          navigator.onLine
        )
          this.timer = setTimeout(
            this.refresh,
            Math.min(pollInterval * 2 ** this.failures, 300000),
          );
      });
    return this.running;
  };
  activity = () => {
    clearTimeout(this.timer);
    if (document.hidden || !navigator.onLine) {
      this.controller?.abort();
      this.running = null;
      if (!navigator.onLine)
        this.emit({
          ...this.state,
          loading: false,
          error: "ইন্টারনেট সংযোগ নেই; তথ্য হালনাগাদ হয়নি।",
        });
    } else void this.refresh();
  };
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    if (this.listeners.size === 1) {
      document.addEventListener("visibilitychange", this.activity);
      window.addEventListener("online", this.activity);
      window.addEventListener("offline", this.activity);
      if (!document.hidden) void this.refresh();
    }
    return () => {
      this.listeners.delete(listener);
      if (!this.listeners.size) {
        this.stop();
      }
    };
  };
  stop() {
    clearTimeout(this.timer);
    this.controller?.abort();
    this.running = null;
    document.removeEventListener("visibilitychange", this.activity);
    window.removeEventListener("online", this.activity);
    window.removeEventListener("offline", this.activity);
  }
}
window.addEventListener("gridwatch-session-ended", () => {
  entries.forEach((e) => {
    e.stop();
    e.emit({ ...empty });
  });
  entries.clear();
});
export function usePolling<T>(path: string | null, userId: string) {
  const entry = useMemo(() => {
    if (!path) return null;
    const key = `${userId}:${path}`;
    if (entries.get(key)?.state.status === 404) {
      entries.get(key)?.stop();
      entries.delete(key);
    }
    if (!entries.has(key)) {
      if (entries.size >= 32) {
        for (const [oldKey, old] of entries) {
          if (!old.listeners.size) {
            old.stop();
            entries.delete(oldKey);
            break;
          }
        }
      }
      entries.set(key, new Entry(path));
    }
    return entries.get(key)! as Entry<T>;
  }, [path, userId]);
  const snapshot = useSyncExternalStore(
    entry?.subscribe || (() => () => {}),
    () => entry?.state || empty,
  );
  return {
    ...snapshot,
    refresh: entry?.refresh || (() => Promise.resolve()),
    stale:
      !!snapshot.error ||
      (!!snapshot.retrievedAt &&
        Date.now() - Date.parse(snapshot.retrievedAt) > pollInterval * 2),
  };
}
