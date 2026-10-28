import { useEffect, useState } from "react";
import { api, shortTime, type Page, type Report } from "./client";
import toast from "react-hot-toast";
export function PublicationActions({
  kind,
  item,
  reload,
}: {
  kind: "notices" | "schedules";
  item: { id: string; version: number; lifecycle: string };
  reload: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <div className="form-stack">
      <span>
        {item.lifecycle} · সংস্করণ {item.version}
      </span>
      <div className="inline-actions">
        {(kind === "notices"
          ? ["publish", "withdraw", "archive"]
          : ["publish", "archive"]
        ).map((action) => (
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy}
            key={action}
            onClick={async () => {
              if (!confirm("এই পরিবর্তন নিশ্চিত করবেন?")) return;
              setBusy(true);
              setError("");
              try {
                await api(`/api/admin/${kind}/${item.id}/${action}`, {
                  method: "POST",
                  body: JSON.stringify({ version: item.version }),
                });
                toast.success("পরিবর্তন সংরক্ষিত");
                reload();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {
              { publish: "প্রকাশ", withdraw: "প্রত্যাহার", archive: "আর্কাইভ" }[
                action
              ]
            }
          </button>
        ))}
      </div>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
export function ObservationPanel({ areaId }: { areaId: string }) {
  const [summary, setSummary] = useState<{
      counts: Record<string, number>;
      latest_observed_at: string | null;
    } | null>(null),
    [reports, setReports] = useState<Report[]>([]),
    [episodes, setEpisodes] = useState<
      {
        id: string;
        started_at: string | null;
        ended_at: string | null;
        duration_seconds: number | null;
        is_open: boolean;
      }[]
    >([]),
    [error, setError] = useState(""),
    [version, setVersion] = useState(0);
  useEffect(() => {
    const c = new AbortController();
    setSummary(null);
    setError("");
    Promise.all([
      api<Page<Report>>("/api/me/reports", { signal: c.signal }),
      api<{ items: typeof episodes }>("/api/me/episodes", { signal: c.signal }),
      areaId
        ? api<typeof summary>(`/api/reports/summary?location_id=${areaId}`, {
            signal: c.signal,
          })
        : Promise.resolve(null),
    ])
      .then(([r, e, s]) => {
        if (!c.signal.aborted) {
          setReports(r.items);
          setEpisodes(e.items);
          setSummary(s);
        }
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [areaId, version]);
  return (
    <section className="section-gap">
      <button className="btn btn-sm" onClick={() => setVersion(version + 1)}>
        রিপোর্ট ও ইতিহাস রিফ্রেশ
      </button>
      {error && <p role="alert">{error}</p>}
      <h2>ব্যবহারকারীর রিপোর্ট · গত এক ঘণ্টা</h2>
      {summary ? (
        <p>
          বিদ্যুৎ নেই: {summary.counts.power_off} · এসেছে:{" "}
          {summary.counts.power_back} · এখনো নেই: {summary.counts.still_off}।
          সর্বশেষ:{" "}
          {summary.latest_observed_at
            ? shortTime(summary.latest_observed_at)
            : "তথ্য অনুপস্থিত"}
          । এটি এলাকার যাচাইকৃত অবস্থা নয়।
        </p>
      ) : (
        <p>এলাকা বাছুন; তথ্য অনুপস্থিত মানে বিদ্যুৎ আছে নয়।</p>
      )}
      <h2>আমার রিপোর্ট</h2>
      {reports.length ? (
        reports.map((r) => (
          <p key={r.id}>
            {r.kind} · {shortTime(r.observed_at)} ·{" "}
            {(r as Report & { moderation: string }).moderation}
          </p>
        ))
      ) : (
        <p>কোনো ব্যক্তিগত রিপোর্ট নেই।</p>
      )}
      <h2>আমার সংযোগের বিভ্রাট ইতিহাস</h2>
      {episodes.map((e) => (
        <p key={e.id}>
          শুরু: {e.started_at ? shortTime(e.started_at) : "অজানা"} → শেষ:{" "}
          {e.ended_at ? shortTime(e.ended_at) : "অজানা"} · সময়কাল:{" "}
          {e.duration_seconds === null
            ? "অজানা"
            : `${e.duration_seconds / 60} মিনিট`}
        </p>
      ))}
    </section>
  );
}

export function PublishedSchedules() {
  const [items, setItems] = useState<
      (import("./client").Schedule & { window_state: string })[]
    >([]),
    [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    api<Page<import("./client").Schedule & { window_state: string }>>(
      "/api/schedules?page_size=20",
      { signal: c.signal },
    )
      .then((r) => {
        if (!c.signal.aborted) setItems(r.items);
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, []);
  return (
    <section className="section-gap">
      <h2>ঘোষিত সময়সূচি</h2>
      <p>
        সময়সূচি বাস্তবে বিদ্যুৎ বন্ধ বা ফেরার প্রমাণ নয়। সময় বাংলাদেশ
        (UTC+6)।
      </p>
      {error && <p role="alert">{error}</p>}
      {items.map((s) => (
        <details key={s.id} className="record">
          <summary>
            {shortTime(s.starts_at)} → {shortTime(s.ends_at)} · {s.status}
          </summary>
          <p>
            {
              {
                upcoming: "আসন্ন",
                within_announced_window: "ঘোষিত সময়ের মধ্যে",
                announced_window_ended: "ঘোষিত সময় শেষ",
              }[s.window_state]
            }{" "}
            · {s.category}
          </p>
          <p>
            আওতা:{" "}
            {s.coverage_scope === "named_locations"
              ? "শুধু নামযুক্ত এলাকা"
              : "সমগ্র নির্বাচিত প্রশাসনিক এলাকা"}{" "}
            · {s.coverage.map((x) => x.name_bn).join(" / ")}
          </p>
          <button
            type="button"
            className="btn btn-sm"
            onClick={async () => {
              try {
                const n = await api<import("./client").Notice>(
                  `/api/notices/${s.notice_id}`,
                );
                window.open(n.source_url, "_blank", "noopener,noreferrer");
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            মূল নোটিশের উৎস
          </button>
        </details>
      ))}
      {!items.length && !error && <p>তথ্য অনুপস্থিত।</p>}
    </section>
  );
}

export function ReportReview() {
  const [items, setItems] = useState<(Report & { moderation: string })[]>([]),
    [page, setPage] = useState(1),
    [total, setTotal] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [version, setVersion] = useState(0);
  useEffect(() => {
    const c = new AbortController();
    api<Page<Report & { moderation: string }>>(
      `/api/admin/reports?page=${page}`,
      { signal: c.signal },
    )
      .then((r) => {
        if (!c.signal.aborted) {
          setItems(r.items);
          setTotal(r.total);
        }
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [page, version]);
  return (
    <details className="section-gap">
      <summary>ব্যক্তিগত রিপোর্ট পর্যালোচনা · প্রাথমিক grouping</summary>
      {error && <p role="alert">{error}</p>}
      {items.map((r) => (
        <form
          key={r.id}
          className="record"
          onSubmit={async (e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            setBusy(true);
            setError("");
            try {
              await api(`/api/admin/reports/${r.id}/moderate`, {
                method: "POST",
                body: JSON.stringify({
                  state: data.get("state"),
                  reason: data.get("reason"),
                  candidate_event_id: data.get("event") || null,
                }),
              });
              toast.success("পর্যালোচনা সংরক্ষিত");
              setVersion(version + 1);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <p>
            {r.kind} · {shortTime(r.observed_at)} · {r.moderation}
          </p>
          <label>
            পর্যালোচনার সিদ্ধান্ত
            <select name="state" className="select" defaultValue={r.moderation}>
              <option value="accepted">গৃহীত ব্যক্তিগত পর্যবেক্ষণ</option>
              <option value="pending">পর্যালোচনাধীন</option>
              <option value="rejected">সারাংশ থেকে বাদ</option>
            </select>
          </label>
          <label>
            কারণ
            <input
              className="input"
              name="reason"
              minLength={5}
              maxLength={500}
              required
            />
          </label>
          <label>
            সংশ্লিষ্ট প্রাথমিক event ID (ঐচ্ছিক)
            <input className="input" name="event" />
          </label>
          <button className="btn btn-sm" disabled={busy}>
            পর্যালোচনা সংরক্ষণ
          </button>
        </form>
      ))}
      <button
        className="btn btn-sm"
        disabled={page === 1}
        onClick={() => setPage(page - 1)}
      >
        পূর্ববর্তী রিপোর্ট
      </button>
      <button
        className="btn btn-sm"
        disabled={page * 20 >= total}
        onClick={() => setPage(page + 1)}
      >
        পরবর্তী রিপোর্ট
      </button>
    </details>
  );
}
