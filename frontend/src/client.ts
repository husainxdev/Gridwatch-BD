export type User = {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "user";
};
export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
export type Location = {
  id: string;
  parent_id: string | null;
  ancestor_names?: string[];
  aliases: string[];
  kind: string;
  name_bn: string;
  name_en: string;
  slug: string;
  verification_status: "verified" | "unverified";
  source_url: string | null;
  updated_at: string;
};
export type Notice = {
  version: number;
  lifecycle: string;
  is_demo: boolean;
  id: string;
  title: string;
  body: string;
  source_url: string;
  publisher: string;
  published_at: string | null;
  verification_status: string;
  updated_at: string;
};
export type Schedule = {
  version: number;
  lifecycle: string;
  category: string;
  coverage: { id: string; name_bn: string }[];
  coverage_scope: string;
  id: string;
  notice_id: string;
  location_id: string;
  starts_at: string;
  ends_at: string;
  status: string;
  updated_at: string;
};
export type Report = {
  id: string;
  location_id: string;
  kind: string;
  observed_at: string;
  created_at: string;
  scope: string;
};
export type Event = {
  id: string;
  location_id: string;
  started_at: string;
  restored_at: string | null;
  start_evidence: string;
  restoration_evidence: string | null;
  verified_at: string;
};
const base = import.meta.env.VITE_API_BASE_URL || "";
let accessToken: string | null = null;
let refreshing: Promise<{ access_token: string; user: User }> | null = null;
export function renewToken() {
  if (!refreshing)
    refreshing = api<{ access_token: string; user: User }>(
      "/api/auth/refresh",
      { method: "POST" },
      false,
    )
      .then((result) => {
        setAccessToken(result.access_token);
        return result;
      })
      .catch((error) => {
        setAccessToken(null);
        throw error;
      })
      .finally(() => {
        refreshing = null;
      });
  return refreshing;
}
export function setAccessToken(value: string | null) {
  accessToken = value;
  if (value === null)
    window.dispatchEvent(new Event("gridwatch-session-ended"));
}
export function csrf() {
  return (
    document.cookie
      .split("; ")
      .find((v) => v.startsWith("gridwatch_csrf="))
      ?.split("=")[1] || ""
  );
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const attemptedAccessToken = accessToken;
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (["POST", "PUT", "DELETE"].includes(options.method || ""))
    headers.set("X-CSRF-Token", csrf());
  const response = await fetch(base + path, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (
    response.status === 401 &&
    retry &&
    accessToken &&
    path != "/api/auth/refresh"
  ) {
    try {
      // Another request may have already refreshed while this 401 was in flight.
      if (attemptedAccessToken === accessToken) await renewToken();
      return api<T>(path, options, false);
    } catch {
      setAccessToken(null);
    }
  }
  if (!response.ok) {
    let detail = "অনুরোধটি সম্পন্ন করা যায়নি।";
    try {
      const data = await response.json();
      detail = Array.isArray(data.fields)
        ? data.fields
            .map(
              (f: { field: string; message: string }) =>
                `${f.field.replace(/^body\./, "")}: ${f.message}`,
            )
            .join("; ")
        : typeof data.detail === "string"
          ? data.detail
          : detail;
    } catch {}
    throw new Error(detail);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export function shortTime(value: string | null) {
  if (!value) return "প্রকাশের সময় অজানা";
  return new Intl.DateTimeFormat("bn-BD", {
    timeZone: "Asia/Dhaka",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
export function localInputTime(date: Date) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Dhaka",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value;
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}
export function bdToIso(value: string) {
  return new Date(value + ":00+06:00").toISOString();
}
