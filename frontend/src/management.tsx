import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "./navigation";
import { api, bdToIso, shortTime, type Page } from "./client";
import { Card } from "./components/ui";
import toast from "react-hot-toast";

export function useRequest<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    setLoading(true);
    api<T>(path, { signal: c.signal })
      .then((x) => {
        if (!c.signal.aborted) setData(x);
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, [path]);
  return { data, error, loading };
}
export function useList<T>(endpoint: string, version = 0) {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const query = new URLSearchParams(params);
  query.delete("tab");
  query.set("page_size", "10");
  query.set("v", String(version));
  const list = useRequest<Page<T>>(`${endpoint}?${query}`);
  const update = (name: string, value: string) =>
    setParams((old) => {
      const next = new URLSearchParams(old);
      if (value) next.set(name, value);
      else next.delete(name);
      if (name !== "page") next.delete("page");
      return next;
    });
  useEffect(() => {
    if (list.data && page > 1 && !list.data.items.length)
      update("page", String(Math.max(1, Math.ceil(list.data.total / 10))));
  }, [list.data]); // server-confirmed deletion can empty the last page
  return {
    ...list,
    params,
    update,
    page,
    clear: () =>
      setParams(params.has("tab") ? { tab: params.get("tab")! } : {}),
  };
}
type ListState = {
  params: URLSearchParams;
  update: (key: string, value: string) => void;
  page: number;
  clear: () => void;
  error: string;
  loading: boolean;
  data: Page<unknown> | null;
};
export function ListControls({
  list,
  statuses = [],
  location = false,
  office = false,
  category = false,
  dates = true,
  sorting = true,
  kinds = [],
}: {
  list: ListState;
  statuses?: string[];
  location?: boolean;
  office?: boolean;
  category?: boolean;
  dates?: boolean;
  sorting?: boolean;
  kinds?: string[];
}) {
  const query = list.params.get("search") || "";
  const [search, setSearch] = useState(query);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    setSearch(query);
    if (timer.current) clearTimeout(timer.current);
  }, [query]);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  return (
    <section className="list-controls" aria-label="তালিকার ফিল্টার">
      <div className="toolbar">
        <label>
          খুঁজুন
          <input
            className="input"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              if (timer.current) clearTimeout(timer.current);
              const value = e.target.value;
              timer.current = setTimeout(
                () => list.update("search", value),
                300,
              );
            }}
          />
        </label>
        {!!statuses.length && (
          <label>
            অবস্থা
            <select
              className="select"
              value={list.params.get("status") || ""}
              onChange={(e) => list.update("status", e.target.value)}
            >
              <option value="">সব</option>
              {statuses.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
        )}
        {sorting && (
          <label>
            ক্রম
            <select
              className="select"
              value={list.params.get("sort") || "newest"}
              onChange={(e) => list.update("sort", e.target.value)}
            >
              <option value="newest">নতুন আগে</option>
              <option value="oldest">পুরোনো আগে</option>
              <option value="name">নাম</option>
              <option value="time">পর্যবেক্ষণ / শুরুর সময়</option>
            </select>
          </label>
        )}
      </div>
      <details>
        <summary>আরও ফিল্টার</summary>
        <div className="toolbar">
          {!!kinds.length && (
            <label>
              ধরন
              <select
                className="select"
                value={list.params.get("kind") || ""}
                onChange={(e) => list.update("kind", e.target.value)}
              >
                <option value="">সব</option>
                {kinds.map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
            </label>
          )}
          {location && (
            <label>
              এলাকার ID
              <input
                className="input"
                value={list.params.get("location_id") || ""}
                onChange={(e) => list.update("location_id", e.target.value)}
              />
            </label>
          )}
          {office && (
            <label>
              প্রকাশক / অফিস
              <input
                className="input"
                value={list.params.get("office") || ""}
                onChange={(e) => list.update("office", e.target.value)}
              />
            </label>
          )}
          {category && (
            <label>
              বিভাগ
              <input
                className="input"
                value={list.params.get("category") || ""}
                onChange={(e) => list.update("category", e.target.value)}
              />
            </label>
          )}
          {dates &&
            ["start", "end"].map((k) => (
              <label key={k}>
                {k === "start" ? "থেকে" : "এর আগে"} · বাংলাদেশ
                <input
                  type="date"
                  className="input"
                  value={(list.params.get(k) || "").slice(0, 10)}
                  onChange={(e) =>
                    list.update(
                      k,
                      e.target.value ? e.target.value + "T00:00:00+06:00" : "",
                    )
                  }
                />
              </label>
            ))}
        </div>
      </details>
      <p className="hint">
        সক্রিয় ফিল্টার:{" "}
        {Array.from(list.params.entries())
          .filter(([k]) => !["tab", "page"].includes(k))
          .map(([k, v]) => `${k}: ${v}`)
          .join(" · ") || "নেই"}
      </p>
      <button className="btn btn-sm" onClick={list.clear}>
        ফিল্টার মুছুন
      </button>
      {list.loading && <p role="status">লোড হচ্ছে…</p>}
      {list.error && <p role="alert">{list.error}</p>}
      {list.data && (
        <div className="pager">
          <span>
            মোট {list.data.total} · পৃষ্ঠা {list.page}
          </span>
          <button
            className="btn btn-sm"
            disabled={list.page <= 1}
            onClick={() => list.update("page", String(list.page - 1))}
          >
            পূর্ববর্তী
          </button>
          <button
            className="btn btn-sm"
            disabled={list.page * 10 >= list.data.total}
            onClick={() => list.update("page", String(list.page + 1))}
          >
            পরবর্তী
          </button>
        </div>
      )}
      {list.data?.total === 0 && <p>এই ফিল্টারে কোনো রেকর্ড নেই।</p>}
    </section>
  );
}
export function AdminOverview() {
  const result = useRequest<Record<string, number>>("/api/admin/overview");
  const cards = [
    [
      "draft_notices",
      "খসড়া নোটিশ",
      "notices",
      "draft",
      "ডেমো বাদে সব খসড়া; যাচাই ও প্রকাশের অপেক্ষায়।",
    ],
    [
      "upcoming_schedules",
      "আসন্ন ঘোষিত সময়সূচি",
      "schedules",
      "published",
      "যাচাইকৃত প্রকাশিত নোটিশের সক্রিয় সময়সূচি, শুরু এখন বা পরে।",
    ],
    [
      "pending_reports",
      "পর্যালোচনাধীন রিপোর্ট",
      "reports",
      "pending",
      "ব্যক্তিগত পর্যবেক্ষণ; নিশ্চিত এলাকার বিভ্রাট নয়।",
    ],
    [
      "unrestored_events",
      "পুনরুদ্ধারের তথ্যবিহীন ঘটনা",
      "events",
      "open",
      "প্রমাণসহ রেকর্ড, ফেরার আলাদা প্রমাণ নেই। Candidate registry নেই।",
    ],
  ];
  return (
    <>
      <h2>কাজের সারাংশ</h2>
      {result.error && <p role="alert">{result.error}</p>}
      <div className="overview-grid">
        {cards.map(([key, title, tab, status, description]) => (
          <Card key={key} title={title}>
            <strong>{result.data?.[key] ?? "…"}</strong>
            <p>{description}</p>
            <Link
              className="btn"
              to={`/admin?tab=${tab}&status=${status}${key === "upcoming_schedules" ? `&start=${encodeURIComponent(new Date().toISOString())}` : ""}`}
            >
              তালিকা দেখুন
            </Link>
          </Card>
        ))}
      </div>
    </>
  );
}
export function AuditTrail({ entity, id }: { entity: string; id: string }) {
  const [open, setOpen] = useState(false);
  return (
    <details onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>পরিবর্তনের ইতিহাস</summary>
      {open && <AuditRows entity={entity} id={id} />}
    </details>
  );
}
function AuditRows({ entity, id }: { entity: string; id: string }) {
  const result = useRequest<
    Page<{
      id: string;
      actor_id: string;
      action: string;
      entity_type: string;
      created_at: string;
      snapshot: unknown;
    }>
  >(`/api/admin/list/audit?search=${id}&page_size=100&sort=oldest`);
  return (
    <>
      {result.error && <p role="alert">{result.error}</p>}
      {result.data?.items
        .filter((x) => x.entity_type === entity)
        .map((x) => (
          <div className="record" key={x.id}>
            <span>
              {shortTime(x.created_at)} · {x.action} · actor {x.actor_id}
            </span>
            <pre className="audit-json">
              {JSON.stringify(x.snapshot, null, 2)}
            </pre>
          </div>
        ))}
      {result.data && result.data.total > 100 && (
        <Link to={`/admin?tab=audit&search=${id}`}>
          সমস্ত পরিবর্তনের পৃষ্ঠাভিত্তিক তালিকা
        </Link>
      )}
    </>
  );
}
export function AdminAudit() {
  const list = useList<{
    id: string;
    entity_type: string;
    entity_id: string;
    action: string;
    created_at: string;
    snapshot: unknown;
  }>("/api/admin/list/audit");
  return (
    <Card title="অ্যাডমিন পরিবর্তনের ইতিহাস">
      <ListControls list={list} />
      <div className="audit-table">
        <table className="table">
          <caption>পরিবর্তন ও সংরক্ষিত প্রমাণ · কেবল অ্যাডমিন</caption>
          <thead>
            <tr>
              <th>রেকর্ড</th>
              <th>কাজ</th>
              <th>সময়</th>
              <th>বিবরণ</th>
            </tr>
          </thead>
          <tbody>
            {list.data?.items.map((x) => (
              <tr key={x.id}>
                <td>
                  {x.entity_type}
                  <br />
                  {x.entity_id}
                </td>
                <td>{x.action}</td>
                <td>{shortTime(x.created_at)}</td>
                <td>
                  <details>
                    <summary>বিস্তারিত</summary>
                    <pre className="audit-json">
                      {JSON.stringify(x.snapshot, null, 2)}
                    </pre>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
export function OfficeDirectory() {
  const list = useList<{ publisher: string; notices: number }>(
    "/api/admin/offices",
  );
  return (
    <Card title="নোটিশে উল্লিখিত প্রকাশক">
      <p>
        এখানে নোটিশে লেখা প্রকাশকের নাম রয়েছে। এটি যাচাইকৃত বিদ্যুৎ অফিসের
        registry নয়। উৎস-পর্যালোচিত অফিস ও mapping পৃথক registry পাতায়
        পরিচালিত হয়। প্রশাসনিক সীমানা থেকে feeder নির্ধারণ করা হয় না।
      </p>
      <ListControls list={list} dates={false} sorting={false} />
      {list.data?.items.map((x) => (
        <div key={x.publisher} className="record">
          <strong>{x.publisher}</strong>
          <span>{x.notices}টি নোটিশ</span>
          <Link
            to={`/admin?tab=notices&office=${encodeURIComponent(x.publisher)}`}
          >
            উৎসসহ নোটিশ দেখুন
          </Link>
        </div>
      ))}
    </Card>
  );
}
type Review = {
  id: string;
  version: number;
  kind: string;
  observed_at: string;
  created_at: string;
  location_name: string;
  location_id: string;
  episode_id: string | null;
  candidate_event_id: string | null;
  moderation: string;
  note: string;
};
export function ModerationWorkspace() {
  const [version, setVersion] = useState(0);
  const list = useList<Review>("/api/admin/list/reports", version);
  return (
    <Card title="ব্যক্তিগত রিপোর্ট পর্যালোচনা">
      <p>
        গৃহীত community report সরকারি নিশ্চিত বিভ্রাট নয়। পর্যালোচনায় মূল
        পর্যবেক্ষণের সময় বদলায় না।
      </p>
      <ListControls
        list={list}
        statuses={["pending", "accepted", "rejected"]}
        kinds={["power_off", "still_off", "power_back"]}
        location
      />
      {list.data?.items.map((r) => (
        <ReviewForm
          key={r.id + ":" + r.version}
          report={r}
          reload={() => setVersion((v) => v + 1)}
        />
      ))}
    </Card>
  );
}
function ReviewForm({
  report: r,
  reload,
}: {
  report: Review;
  reload: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <form
      className="record form-stack"
      onSubmit={async (e) => {
        e.preventDefault();
        if (busy) return;
        const data = new FormData(e.currentTarget);
        if (
          !confirm(
            "এই পর্যালোচনা ব্যক্তিগত ইতিহাস পুনর্গণনা করবে। মূল পর্যবেক্ষণ সংরক্ষিত থাকবে। এগোবেন?",
          )
        )
          return;
        setBusy(true);
        setError("");
        try {
          await api(`/api/admin/reports/${r.id}/moderate`, {
            method: "POST",
            body: JSON.stringify({
              version: r.version,
              state: data.get("state"),
              reason: data.get("reason"),
              candidate_event_id: data.get("event") || null,
            }),
          });
          toast.success("পর্যালোচনা সংরক্ষিত");
          reload();
        } catch (e) {
          setError((e as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <strong>
        {r.location_name} · {r.kind} · {r.moderation}
      </strong>
      <span>
        পর্যবেক্ষণ: {shortTime(r.observed_at)} · জমা: {shortTime(r.created_at)}
      </span>
      <p>{r.note}</p>
      <ReportContext id={r.id} />
      <label>
        পর্যালোচনার সিদ্ধান্ত
        <select className="select" name="state" defaultValue={r.moderation}>
          <option value="accepted">গৃহীত ব্যক্তিগত পর্যবেক্ষণ</option>
          <option value="pending">আরও পর্যালোচনা</option>
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
        সংশ্লিষ্ট event ID · খালি রাখলে association সরবে
        <input
          className="input"
          name="event"
          defaultValue={r.candidate_event_id || ""}
        />
      </label>
      <button className="btn" disabled={busy}>
        পর্যালোচনা সংরক্ষণ
      </button>
      {error && <p role="alert">{error}</p>}
      <AuditTrail entity="reports" id={r.id} />
    </form>
  );
}
function ReportContext({ id }: { id: string }) {
  const [open, setOpen] = useState(false);
  return (
    <details onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>সংশ্লিষ্ট episode ও ঘোষণা</summary>
      {open && <ReportContextContent id={id} />}
    </details>
  );
}
function ReportContextContent({ id }: { id: string }) {
  const r = useRequest<{
    episode: {
      id: string;
      started_at: string | null;
      ended_at: string | null;
    } | null;
    schedules: {
      id: string;
      title: string;
      source_url: string;
      status: string;
      lifecycle: string;
    }[];
  }>(`/api/admin/reports/${id}/context`);
  return (
    <>
      {r.error && <p role="alert">{r.error}</p>}
      <p>Episode: {r.data?.episode?.id || "নেই"}</p>
      <p>
        {r.data?.episode?.started_at
          ? shortTime(r.data.episode.started_at)
          : "শুরু অজানা"}{" "}
        →{" "}
        {r.data?.episode?.ended_at
          ? shortTime(r.data.episode.ended_at)
          : "শেষ অজানা"}
      </p>
      {r.data?.schedules.map((s) => (
        <p key={s.id}>
          <a href={s.source_url} target="_blank" rel="noreferrer">
            {s.title}
          </a>{" "}
          · {s.status} · {s.lifecycle}
        </p>
      ))}
      <p>সময় ও এলাকার মিল; কারণের প্রমাণ নয়। সর্বোচ্চ ২০টি ঘোষণা।</p>
    </>
  );
}
export function TimeField({
  label,
  name,
  value,
  onChange,
}: {
  label: string;
  name?: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label>
      {label} · বাংলাদেশ
      <input
        className="input"
        type="datetime-local"
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
      />
    </label>
  );
}
export function PrivatePanel({ children }: { children: ReactNode }) {
  return <div className="form-stack">{children}</div>;
}
export { bdToIso };

export function NoticeSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (id: string) => void;
}) {
  const [search, setSearch] = useState(""),
    [query, setQuery] = useState(""),
    [page, setPage] = useState(1);
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);
  const result = useRequest<Page<{ id: string; title: string }>>(
    `/api/admin/list/notices?status=published&search=${encodeURIComponent(query)}&page=${page}&page_size=10`,
  );
  return (
    <div className="form-stack">
      <label>
        প্রকাশিত নোটিশ খুঁজুন
        <input
          type="search"
          className="input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      <label>
        যাচাইকৃত প্রকাশিত নোটিশ
        <select
          className="select"
          name="notice_id"
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">বাছুন</option>
          {value && !result.data?.items.some((x) => x.id === value) && (
            <option value={value}>বর্তমান নির্বাচন · {value}</option>
          )}
          {result.data?.items.map((x) => (
            <option key={x.id} value={x.id}>
              {x.title}
            </option>
          ))}
        </select>
      </label>
      {result.error && <p role="alert">{result.error}</p>}
      <div className="pager">
        <button
          type="button"
          className="btn btn-sm"
          disabled={page === 1}
          onClick={() => setPage((p) => p - 1)}
        >
          আগের নোটিশ
        </button>
        <span>{result.data?.total ?? "…"}টি নোটিশ</span>
        <button
          type="button"
          className="btn btn-sm"
          disabled={!result.data || page * 10 >= result.data.total}
          onClick={() => setPage((p) => p + 1)}
        >
          পরের নোটিশ
        </button>
      </div>
    </div>
  );
}
