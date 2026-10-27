import { LocationPicker } from "./components/LocationPicker";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import {
  api,
  bdToIso,
  localInputTime,
  shortTime,
  setAccessToken,
  type Event,
  type Location,
  type Notice,
  type Page,
  type Report,
  type Schedule,
} from "./client";
import { useSession } from "./session";
import { Card, EmptyState, EvidenceBadge } from "./components/ui";

function ErrorBox({ message }: { message: string }) {
  return message ? (
    <div className="alert alert-error" role="alert">
      {message}
    </div>
  ) : null;
}
function Submit({ busy, children }: { busy: boolean; children: ReactNode }) {
  return (
    <button className="btn btn-primary" disabled={busy}>
      {busy ? "অপেক্ষা করুন…" : children}
    </button>
  );
}
function useData<T>(path: string) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<T>(path)
      .then((x) => {
        if (active) setData(x);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return { data, error, loading, reload: () => setVersion((x) => x + 1) };
}
function useAsyncAction(reload?: () => void) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function run(
    action: () => Promise<unknown>,
    success = "সংরক্ষণ হয়েছে",
  ) {
    setBusy(true);
    setError("");
    try {
      await action();
      toast.success(success);
      reload?.();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, run };
}
function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
function Pager({
  page,
  total,
  size,
  onChange,
}: {
  page: number;
  total: number;
  size: number;
  onChange: (n: number) => void;
}) {
  return (
    <div className="pager">
      <span>মোট {total}টি</span>
      <button
        className="btn btn-sm"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        পূর্ববর্তী
      </button>
      <span>
        {page} / {Math.max(1, Math.ceil(total / size))}
      </span>
      <button
        className="btn btn-sm"
        disabled={page * size >= total}
        onClick={() => onChange(page + 1)}
      >
        পরবর্তী
      </button>
    </div>
  );
}
export function AuthPage({
  mode,
}: {
  mode: "login" | "register" | "forgot" | "reset";
}) {
  const { user, signIn, signUp } = useSession();
  const nav = useNavigate(),
    [params] = useSearchParams();
  const [resetToken] = useState(
    () =>
      new URLSearchParams(window.location.hash.slice(1)).get("token") ||
      params.get("token"),
  );
  useEffect(() => {
    if (mode === "reset")
      window.history.replaceState(null, "", window.location.pathname);
  }, [mode]);
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [success, setSuccess] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    const email = String(fd.get("email") || ""),
      password = String(fd.get("password") || "");
    try {
      if (mode === "register" || mode === "reset") {
        const bytes = new TextEncoder().encode(password).length;
        if (bytes < 8 || bytes > 72)
          throw new Error(
            "পাসওয়ার্ড ৮–৭২ UTF-8 বাইট হতে হবে (বাংলা অক্ষরে একাধিক বাইট লাগে)।",
          );
      }
      if (mode === "login") await signIn(email, password);
      if (mode === "register")
        await signUp(email, password, String(fd.get("name") || ""));
      if (mode === "forgot") {
        const x = await api<{ message: string }>(
          "/api/auth/password-reset/request",
          { method: "POST", body: JSON.stringify({ email }) },
        );
        setSuccess(x.message);
        return;
      }
      if (mode === "reset") {
        await api("/api/auth/password-reset/confirm", {
          method: "POST",
          body: JSON.stringify({ token: resetToken, password }),
        });
        setAccessToken(null);
        toast.success("পাসওয়ার্ড বদলানো হয়েছে");
        nav("/login");
        return;
      }
      nav("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (user && (mode === "login" || mode === "register"))
    return <Navigate to="/dashboard" replace />;
  return (
    <div className="auth-wrap">
      <Card
        title={
          {
            login: "অ্যাকাউন্টে প্রবেশ",
            register: "নতুন অ্যাকাউন্ট",
            forgot: "পাসওয়ার্ড পুনরুদ্ধার",
            reset: "নতুন পাসওয়ার্ড",
          }[mode]
        }
      >
        <p className="hint">
          শুধু যাচাইকৃত এলাকা বেছে রিপোর্ট দিন। আপনার রিপোর্ট আপনার সংযোগের
          অভিজ্ঞতা বোঝায়।
        </p>
        <form onSubmit={submit} className="form-stack">
          {mode === "register" && (
            <Field label="নাম">
              <input
                className="input input-bordered"
                name="name"
                required
                minLength={2}
                maxLength={100}
              />
            </Field>
          )}
          {(mode === "login" || mode === "register" || mode === "forgot") && (
            <Field label="ইমেইল">
              <input
                className="input input-bordered"
                type="email"
                name="email"
                required
              />
            </Field>
          )}
          {mode !== "forgot" && (
            <Field label="পাসওয়ার্ড">
              <input
                className="input input-bordered"
                type="password"
                name="password"
                required
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                maxLength={72}
              />
            </Field>
          )}
          <ErrorBox message={error} />
          {success && <div className="alert alert-success">{success}</div>}
          <Submit busy={busy}>
            {mode === "login"
              ? "প্রবেশ করুন"
              : mode === "register"
                ? "অ্যাকাউন্ট খুলুন"
                : mode === "forgot"
                  ? "রিসেট লিংক পাঠান"
                  : "পাসওয়ার্ড বদলান"}
          </Submit>
        </form>
        <div className="auth-links">
          <Link to="/login">প্রবেশ</Link>
          <Link to="/register">নিবন্ধন</Link>
          <Link to="/forgot">পাসওয়ার্ড ভুলে গেছেন?</Link>
        </div>
      </Card>
    </div>
  );
}
export function RequireUser({
  admin = false,
  children,
}: {
  admin?: boolean;
  children: ReactNode;
}) {
  const { user, checking } = useSession();
  if (checking) return <div className="loading-state">সেশন যাচাই হচ্ছে…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin")
    return (
      <div className="alert alert-error">
        এই পাতায় অ্যাডমিন অনুমতি প্রয়োজন।
      </div>
    );
  return <>{children}</>;
}

let rememberedArea = "";
function useAreaSelection() {
  const areas = useData<Page<Location>>("/api/locations?page_size=100");
  const [selected, updateSelected] = useState(rememberedArea);
  const setSelected = (value: string) => {
    rememberedArea = value;
    updateSelected(value);
  };
  const detail = useData<Location>(
    selected ? `/api/locations/${selected}` : "/api/health/live",
  );
  return {
    areas,
    selected,
    setSelected,
    area: selected && detail.data?.id === selected ? detail.data : undefined,
  };
}
function AreaChooser({
  value,
  onChange,
}: {
  items: Location[];
  value: string;
  onChange: (value: string) => void;
}) {
  return <LocationPicker value={value} onChange={onChange} />;
}
export function Dashboard() {
  const { user } = useSession();
  const { areas, selected, setSelected, area } = useAreaSelection();
  const reports = useData<Page<Report>>(
    selected
      ? `/api/reports?location_id=${selected}&page_size=5`
      : "/api/health/live",
  );
  const schedules = useData<Page<Schedule>>(
    selected
      ? `/api/schedules?location_id=${selected}&status=announced&page_size=5`
      : "/api/health/live",
  );
  const events = useData<Page<Event>>(
    selected
      ? `/api/events?location_id=${selected}&page_size=5`
      : "/api/health/live",
  );
  const saved = useData<{ items: Location[] }>("/api/saved-areas");
  const action = useAsyncAction(() => {
    reports.reload();
    saved.reload();
  });
  const [reportBusy, setReportBusy] = useState(false);
  async function report(kind: Report["kind"]) {
    if (!selected) return;
    setReportBusy(true);
    try {
      await api("/api/reports", {
        method: "POST",
        body: JSON.stringify({
          location_id: selected,
          kind,
          observed_at: new Date().toISOString(),
          idempotency_key: crypto.randomUUID(),
        }),
      });
      toast.success("আপনার সংযোগের রিপোর্ট জমা হয়েছে");
      reports.reload();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setReportBusy(false);
    }
  }
  const listed =
    selected && Array.isArray(reports.data?.items) ? reports.data!.items : [];
  const planned =
    selected && Array.isArray(schedules.data?.items)
      ? schedules.data!.items
      : [];
  const historical =
    selected && Array.isArray(events.data?.items) ? events.data!.items : [];
  return (
    <>
      <p className="eyebrow">ব্যক্তিগত ড্যাশবোর্ড</p>
      <h1>স্বাগতম, {user?.display_name}</h1>
      <p className="hint">
        এই পাতা যাচাইকৃত এলাকা ও তার রেকর্ড দেখায়। নীরবতা বিদ্যুৎ থাকার প্রমাণ
        নয়।
      </p>
      <ErrorBox message={areas.error} />
      <Card title="এলাকা নির্বাচন">
        <AreaChooser
          items={areas.data?.items || []}
          value={selected}
          onChange={setSelected}
        />
        {area && (
          <div className="inline-actions">
            <EvidenceBadge>
              {area.verification_status === "verified"
                ? "এলাকা যাচাইকৃত"
                : "যাচাই বাকি"}
            </EvidenceBadge>
            <a href={area.source_url || "#"} target="_blank" rel="noreferrer">
              এলাকার উৎস
            </a>
            <button
              className="btn btn-sm"
              onClick={() =>
                action.run(() =>
                  api(`/api/saved-areas/${area.id}`, { method: "POST" }),
                )
              }
            >
              এলাকা সংরক্ষণ
            </button>
          </div>
        )}
        {!selected && !areas.loading && (
          <EmptyState title="একটি যাচাইকৃত এলাকা বাছুন">
            তালিকা বা অনুসন্ধান থেকে এলাকা বাছুন। এলাকা না থাকলে অ্যাডমিনকে
            প্রথমে পাইলট এলাকা ও উৎস যাচাই করতে হবে। নমুনা এলাকা এখানে আসে না।
          </EmptyState>
        )}
      </Card>
      {selected && (
        <>
          <div className="detail-grid section-gap">
            <Card title="আপনার সংযোগের রিপোর্ট">
              <p className="hint">
                এটি আপনার সংযোগের অবস্থা; পুরো এলাকার সিদ্ধান্ত নয়। একই ধরনের
                রিপোর্ট ১০ মিনিটের মধ্যে আবার দেওয়া যাবে না।
              </p>
              <div className="inline-actions">
                <button
                  className="btn btn-primary"
                  disabled={reportBusy}
                  onClick={() => report("power_off")}
                >
                  বিদ্যুৎ নেই
                </button>
                <button
                  className="btn"
                  disabled={reportBusy}
                  onClick={() => report("power_back")}
                >
                  বিদ্যুৎ ফিরেছে
                </button>
                <button
                  className="btn"
                  disabled={reportBusy}
                  onClick={() => report("still_off")}
                >
                  এখনো নেই
                </button>
              </div>
              {listed.length ? (
                listed.map((x) => (
                  <div className="record" key={x.id}>
                    <strong>
                      {
                        (
                          {
                            power_off: "বিদ্যুৎ নেই",
                            power_back: "বিদ্যুৎ ফিরেছে",
                            still_off: "এখনো নেই",
                          } as Record<string, string>
                        )[x.kind]
                      }
                    </strong>
                    <span>{shortTime(x.observed_at)} · ব্যক্তিগত রিপোর্ট</span>
                  </div>
                ))
              ) : (
                <EmptyState title="কোনো রিপোর্ট নেই">
                  রিপোর্ট না থাকলে বিদ্যুৎ আছে বলা যায় না।
                </EmptyState>
              )}
            </Card>
            <Card title="ঘোষিত সময়সূচি">
              <p className="hint">এগুলো পরিকল্পনা, ঘটেছে এমন প্রমাণ নয়।</p>
              {planned.length ? (
                planned.map((x) => (
                  <div className="record" key={x.id}>
                    <strong>
                      {shortTime(x.starts_at)} → {shortTime(x.ends_at)}
                    </strong>
                    <span>
                      ঘোষিত · সর্বশেষ পরিবর্তন {shortTime(x.updated_at)}
                    </span>
                  </div>
                ))
              ) : (
                <EmptyState title="কোনো ঘোষিত সময়সূচি নেই">
                  এতে বিদ্যুৎ থাকার নিশ্চয়তা নেই।
                </EmptyState>
              )}
            </Card>
          </div>
          <div className="detail-grid section-gap">
            <Activity areaId={selected} />
            <Card title="যাচাইকৃত বিভ্রাটের ইতিহাস">
              {historical.length ? (
                historical.map((x) => (
                  <div className="record" key={x.id}>
                    <strong>
                      {shortTime(x.started_at)} →{" "}
                      {x.restored_at
                        ? shortTime(x.restored_at)
                        : "ফেরার তথ্য নেই"}
                    </strong>
                    <span>শুরুর প্রমাণ: {x.start_evidence}</span>
                    {x.restoration_evidence && (
                      <span>ফেরার প্রমাণ: {x.restoration_evidence}</span>
                    )}
                  </div>
                ))
              ) : (
                <EmptyState title="রেকর্ড করা ঘটনা নেই">
                  সময়সূচি থেকে ইতিহাস তৈরি করা হয় না।
                </EmptyState>
              )}
            </Card>
          </div>
        </>
      )}
      <Card title="সংরক্ষিত এলাকা" className="section-gap">
        {saved.data?.items.length ? (
          saved.data.items.map((x) => (
            <div className="record" key={x.id}>
              <strong>{x.name_bn}</strong>
              <button
                className="btn btn-sm"
                onClick={() =>
                  action.run(() =>
                    api(`/api/saved-areas/${x.id}`, { method: "DELETE" }),
                  )
                }
              >
                সরান
              </button>
            </div>
          ))
        ) : (
          <EmptyState title="এখনো সংরক্ষিত এলাকা নেই">
            যাচাইকৃত এলাকা বেছে সংরক্ষণ করুন।
          </EmptyState>
        )}
      </Card>
    </>
  );
}
function Activity({ areaId }: { areaId: string }) {
  const [start, setStart] = useState(localInputTime(new Date())),
    [end, setEnd] = useState(localInputTime(new Date(Date.now() + 3600000))),
    [result, setResult] = useState<{
      conflicts: Schedule[];
      message: string;
    } | null>(null);
  const action = useAsyncAction();
  return (
    <Card title="কাজের সময় মিলিয়ে দেখুন">
      <p className="hint">
        ঘোষিত সময়সূচির সঙ্গে ওভারল্যাপ খোঁজা হয়। ফলাফল বিদ্যুৎ থাকার নিশ্চয়তা
        নয়।
      </p>
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          action.run(async () => {
            setResult(
              await api("/api/activities/check", {
                method: "POST",
                body: JSON.stringify({
                  location_id: areaId,
                  starts_at: bdToIso(start),
                  ends_at: bdToIso(end),
                }),
              }),
            );
          }, "সময় মিলিয়ে দেখা হয়েছে");
        }}
      >
        <Field label="শুরু · বাংলাদেশ সময়">
          <input
            className="input input-bordered"
            type="datetime-local"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            required
          />
        </Field>
        <Field label="শেষ · বাংলাদেশ সময়">
          <input
            className="input input-bordered"
            type="datetime-local"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            required
          />
        </Field>
        <ErrorBox message={action.error} />
        <Submit busy={action.busy}>মিলিয়ে দেখুন</Submit>
      </form>
      {result && (
        <div className="record" role="status">
          <strong>
            {result.conflicts.length
              ? `${result.conflicts.length}টি ঘোষিত সংঘর্ষ`
              : "ঘোষিত সংঘর্ষ নেই"}
          </strong>
          <span>{result.message}</span>
          {result.conflicts.map((x) => (
            <span key={x.id}>
              {shortTime(x.starts_at)} → {shortTime(x.ends_at)}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
}

export function NoticeBoard() {
  const [search, setSearch] = useState(""),
    [query, setQuery] = useState(""),
    [page, setPage] = useState(1),
    [sort, setSort] = useState<"newest" | "oldest">("newest");
  const notices = useData<Page<Notice>>(
    `/api/notices?page=${page}&page_size=10&sort=${sort}&search=${encodeURIComponent(query)}`,
  );
  return (
    <>
      <p className="eyebrow">মূল উৎস ও প্রকাশনার সময়</p>
      <h1>নোটিশ ও ঘোষণা</h1>
      <p className="hint">
        প্রতিটি নোটিশের যাচাইয়ের অবস্থা ও মূল লিংক দেখুন। কোনো নোটিশ বাস্তব
        বিভ্রাট নিশ্চিত করে না।
      </p>
      <div className="toolbar">
        <input
          className="input input-bordered"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="শিরোনাম খুঁজুন"
          aria-label="শিরোনাম খুঁজুন"
        />
        <button
          className="btn"
          onClick={() => {
            setQuery(search);
            setPage(1);
          }}
        >
          খুঁজুন
        </button>
        <select
          className="select select-bordered"
          aria-label="ক্রম"
          value={sort}
          onChange={(e) => setSort(e.target.value as "newest" | "oldest")}
        >
          <option value="newest">নতুন আগে</option>
          <option value="oldest">পুরোনো আগে</option>
        </select>
      </div>
      <ErrorBox message={notices.error} />
      {notices.data?.items.length
        ? notices.data.items.map((x) => (
            <Card key={x.id} title={x.title} className="section-gap">
              <div className="inline-actions">
                <EvidenceBadge>
                  {x.verification_status === "verified"
                    ? "যাচাইকৃত"
                    : "যাচাই বাকি"}
                </EvidenceBadge>
                <span>
                  {x.publisher} · {shortTime(x.published_at)}
                </span>
              </div>
              <p>{x.body}</p>
              <a href={x.source_url} target="_blank" rel="noreferrer">
                মূল নোটিশ খুলুন ↗
              </a>
              <p className="fine-print">
                সর্বশেষ পরিবর্তন: {shortTime(x.updated_at)}
              </p>
            </Card>
          ))
        : !notices.loading && (
            <Card title="নোটিশ নেই">
              <EmptyState title="এখনো কোনো নোটিশ নেই">
                অ্যাডমিন যাচাইযোগ্য মূল উৎস যুক্ত করলে এখানে দেখা যাবে।
              </EmptyState>
            </Card>
          )}
      {notices.data && (
        <Pager
          page={page}
          total={notices.data.total}
          size={10}
          onChange={setPage}
        />
      )}
    </>
  );
}
export function Admin() {
  const [tab, setTab] = useState<"areas" | "notices" | "schedules" | "events">(
    "areas",
  );
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((x) => x + 1);
  return (
    <>
      <p className="eyebrow">সীমিত প্রশাসনিক প্রবেশাধিকার</p>
      <h1>অ্যাডমিন ড্যাশবোর্ড</h1>
      <p className="hint">
        প্রকাশের আগে মূল উৎস ও এলাকার সীমানা হাতে যাচাই করুন। প্রশাসনিক যাচাই
        নিজে সরকারি অনুমোদন নয়।
      </p>
      <div className="toolbar admin-tabs">
        {(
          [
            ["areas", "এলাকা"],
            ["notices", "নোটিশ"],
            ["schedules", "সময়সূচি"],
            ["events", "ঘটনা"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            className={`btn ${tab === key ? "btn-primary" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "areas" && <AdminAreas version={version} reload={reload} />}
      {tab === "notices" && <AdminNotices version={version} reload={reload} />}
      {tab === "schedules" && (
        <AdminSchedules version={version} reload={reload} />
      )}
      {tab === "events" && <AdminEvents version={version} reload={reload} />}
    </>
  );
}
function AdminAreas({
  version,
  reload,
}: {
  version: number;
  reload: () => void;
}) {
  const list = useData<Page<Location>>(
    `/api/locations?page_size=100&v=${version}`,
  );
  const action = useAsyncAction(reload);
  const [edit, setEdit] = useState<Location | null>(null);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      body = {
        name_bn: f.get("name_bn"),
        name_en: f.get("name_en"),
        slug: f.get("slug"),
        kind: f.get("kind"),
        parent_id: f.get("parent_id") || null,
        aliases: String(f.get("aliases") || "")
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
      };
    if (
      await action.run(() =>
        api(edit ? `/api/admin/locations/${edit.id}` : "/api/admin/locations", {
          method: edit ? "PUT" : "POST",
          body: JSON.stringify(body),
        }),
      )
    )
      setEdit(null);
  }
  return (
    <div className="admin-grid">
      <Card title={edit ? "এলাকা সম্পাদনা" : "নতুন এলাকা"}>
        <p className="hint">
          বাস্তব প্রশাসনিক সম্পর্ক ও উৎস যাচাইয়ের আগে এলাকাকে verified করবেন
          না।
        </p>
        <form className="form-stack" onSubmit={submit} key={edit?.id || "new"}>
          <Field label="বাংলা নাম">
            <input
              name="name_bn"
              className="input input-bordered"
              defaultValue={edit?.name_bn}
              required
              minLength={2}
            />
          </Field>
          <Field label="English name">
            <input
              name="name_en"
              className="input input-bordered"
              defaultValue={edit?.name_en}
              required
              minLength={2}
            />
          </Field>
          <Field label="বিকল্প নাম (কমা দিয়ে আলাদা করুন)">
            <input
              name="aliases"
              className="input input-bordered"
              defaultValue={edit?.aliases?.join(", ") || ""}
            />
          </Field>
          <Field label="Slug">
            <input
              name="slug"
              className="input input-bordered"
              defaultValue={edit?.slug}
              required
              pattern="[a-z0-9]+(-[a-z0-9]+)*"
            />
          </Field>
          <Field label="স্তর">
            <select
              name="kind"
              className="select select-bordered"
              defaultValue={edit?.kind || "division"}
            >
              {[
                "division",
                "district",
                "upazila",
                "city_corporation",
                "union",
                "ward",
                "village",
                "neighborhood",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </Field>
          <Field label="মূল এলাকা">
            <select
              name="parent_id"
              className="select select-bordered"
              defaultValue={edit?.parent_id || ""}
            >
              <option value="">কোনোটি নয়</option>
              {list.data?.items
                .filter((x) => x.id !== edit?.id)
                .map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name_bn} · {x.kind}
                  </option>
                ))}
            </select>
          </Field>
          <ErrorBox message={action.error} />
          <Submit busy={action.busy}>সংরক্ষণ</Submit>
          {edit && (
            <button type="button" className="btn" onClick={() => setEdit(null)}>
              বাতিল
            </button>
          )}
        </form>
      </Card>
      <Card title="এলাকার তালিকা">
        <ErrorBox message={list.error} />
        {list.data?.items.map((x) => (
          <div className="record" key={x.id}>
            <strong>
              {x.name_bn} · {x.kind}
            </strong>
            <span>
              {x.verification_status} · {x.slug}
            </span>
            <div className="inline-actions">
              <button className="btn btn-sm" onClick={() => setEdit(x)}>
                সম্পাদনা
              </button>
              {x.verification_status !== "verified" && (
                <button
                  className="btn btn-sm"
                  onClick={() => {
                    const url = window.prompt(
                      "যাচাই করা মূল উৎসের HTTPS লিংক দিন",
                    );
                    if (url)
                      action.run(() =>
                        api(`/api/admin/locations/${x.id}/verify`, {
                          method: "POST",
                          body: JSON.stringify({ source_url: url }),
                        }),
                      );
                  }}
                >
                  উৎস দিয়ে যাচাই
                </button>
              )}
              <button
                className="btn btn-sm btn-error btn-outline"
                onClick={() => {
                  if (window.confirm("এই এলাকা মুছবেন?"))
                    action.run(() =>
                      api(`/api/admin/locations/${x.id}`, { method: "DELETE" }),
                    );
                }}
              >
                মুছুন
              </button>
            </div>
          </div>
        ))}
        {!list.data?.items.length && (
          <EmptyState title="এলাকা নেই">
            প্রথমে division, তারপর জেলা ও ছোট এলাকা তৈরি করুন।
          </EmptyState>
        )}
      </Card>
    </div>
  );
}
function AdminNotices({
  version,
  reload,
}: {
  version: number;
  reload: () => void;
}) {
  const [page, setPage] = useState(1),
    [search, setSearch] = useState(""),
    [query, setQuery] = useState("");
  const list = useData<Page<Notice>>(
    `/api/notices?page=${page}&page_size=10&search=${encodeURIComponent(query)}&v=${version}`,
  );
  const action = useAsyncAction(reload),
    [edit, setEdit] = useState<Notice | null>(null);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      title: f.get("title"),
      body: f.get("body"),
      source_url: f.get("source_url"),
      publisher: f.get("publisher"),
      published_at: bdToIso(String(f.get("published_at"))),
    };
    if (
      await action.run(() =>
        api(edit ? `/api/admin/notices/${edit.id}` : "/api/admin/notices", {
          method: edit ? "PUT" : "POST",
          body: JSON.stringify(body),
        }),
      )
    )
      setEdit(null);
  }
  return (
    <div className="admin-grid">
      <Card title={edit ? "নোটিশ সম্পাদনা" : "মূল নোটিশ যোগ"}>
        <form className="form-stack" onSubmit={submit} key={edit?.id || "new"}>
          <Field label="শিরোনাম">
            <input
              name="title"
              className="input input-bordered"
              defaultValue={edit?.title}
              required
              minLength={4}
            />
          </Field>
          <Field label="বিবরণ">
            <textarea
              name="body"
              className="textarea textarea-bordered"
              defaultValue={edit?.body}
              required
              minLength={10}
            />
          </Field>
          <Field label="মূল উৎসের HTTPS লিংক">
            <input
              name="source_url"
              type="url"
              className="input input-bordered"
              defaultValue={edit?.source_url}
              required
            />
          </Field>
          <Field label="প্রকাশক">
            <input
              name="publisher"
              className="input input-bordered"
              defaultValue={edit?.publisher}
              required
            />
          </Field>
          <Field label="প্রকাশের সময় · বাংলাদেশ">
            <input
              name="published_at"
              type="datetime-local"
              className="input input-bordered"
              defaultValue={
                edit
                  ? localInputTime(new Date(edit.published_at))
                  : localInputTime(new Date())
              }
              required
            />
          </Field>
          <ErrorBox message={action.error} />
          <Submit busy={action.busy}>সংরক্ষণ</Submit>
          {edit && (
            <button type="button" className="btn" onClick={() => setEdit(null)}>
              বাতিল
            </button>
          )}
        </form>
      </Card>
      <Card title="নোটিশ তালিকা">
        <div className="toolbar">
          <input
            className="input input-bordered"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="খুঁজুন"
          />
          <button
            className="btn"
            onClick={() => {
              setPage(1);
              setQuery(search);
            }}
          >
            খুঁজুন
          </button>
        </div>
        {list.data?.items.map((x) => (
          <div className="record" key={x.id}>
            <strong>{x.title}</strong>
            <span>
              {x.verification_status} · {shortTime(x.published_at)}
            </span>
            <a href={x.source_url} target="_blank" rel="noreferrer">
              মূল উৎস ↗
            </a>
            <div className="inline-actions">
              <button className="btn btn-sm" onClick={() => setEdit(x)}>
                সম্পাদনা
              </button>
              {x.verification_status !== "verified" && (
                <button
                  className="btn btn-sm"
                  onClick={() =>
                    action.run(() =>
                      api(`/api/admin/notices/${x.id}/verify`, {
                        method: "POST",
                      }),
                    )
                  }
                >
                  যাচাই
                </button>
              )}
              <button
                className="btn btn-sm btn-outline btn-error"
                onClick={() => {
                  if (window.confirm("নোটিশ মুছবেন?"))
                    action.run(() =>
                      api(`/api/admin/notices/${x.id}`, { method: "DELETE" }),
                    );
                }}
              >
                মুছুন
              </button>
            </div>
          </div>
        ))}
        <ErrorBox message={list.error} />
        {list.data && (
          <Pager
            page={page}
            total={list.data.total}
            size={10}
            onChange={setPage}
          />
        )}
      </Card>
    </div>
  );
}
function AdminSchedules({
  version,
  reload,
}: {
  version: number;
  reload: () => void;
}) {
  const areas = useData<Page<Location>>(
      `/api/locations?page_size=100&v=${version}`,
    ),
    notices = useData<Page<Notice>>(`/api/notices?page_size=100&v=${version}`),
    list = useData<Page<Schedule>>(`/api/schedules?page_size=100&v=${version}`);
  const action = useAsyncAction(reload),
    [edit, setEdit] = useState<Schedule | null>(null);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      notice_id: f.get("notice_id"),
      location_id: f.get("location_id"),
      starts_at: bdToIso(String(f.get("starts_at"))),
      ends_at: bdToIso(String(f.get("ends_at"))),
    };
    if (
      await action.run(() =>
        api(edit ? `/api/admin/schedules/${edit.id}` : "/api/admin/schedules", {
          method: edit ? "PUT" : "POST",
          body: JSON.stringify(body),
        }),
      )
    )
      setEdit(null);
  }
  return (
    <div className="admin-grid">
      <Card title={edit ? "সময়সূচি সম্পাদনা" : "ঘোষিত সময়সূচি"}>
        <form className="form-stack" onSubmit={submit} key={edit?.id || "new"}>
          <Field label="যাচাইকৃত নোটিশ">
            <select
              name="notice_id"
              className="select select-bordered"
              required
              defaultValue={edit?.notice_id || ""}
            >
              <option value="">বাছুন</option>
              {notices.data?.items
                .filter((x) => x.verification_status === "verified")
                .map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.title}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="যাচাইকৃত এলাকা">
            <select
              name="location_id"
              className="select select-bordered"
              required
              defaultValue={edit?.location_id || ""}
            >
              <option value="">বাছুন</option>
              {areas.data?.items
                .filter((x) => x.verification_status === "verified")
                .map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name_bn}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="শুরু · বাংলাদেশ">
            <input
              name="starts_at"
              type="datetime-local"
              className="input input-bordered"
              defaultValue={
                edit ? localInputTime(new Date(edit.starts_at)) : ""
              }
              required
            />
          </Field>
          <Field label="শেষ · বাংলাদেশ">
            <input
              name="ends_at"
              type="datetime-local"
              className="input input-bordered"
              defaultValue={edit ? localInputTime(new Date(edit.ends_at)) : ""}
              required
            />
          </Field>
          <ErrorBox message={action.error} />
          <Submit busy={action.busy}>সংরক্ষণ</Submit>
          {edit && (
            <button className="btn" type="button" onClick={() => setEdit(null)}>
              বাতিল
            </button>
          )}
        </form>
      </Card>
      <Card title="সময়সূচির তালিকা">
        {list.data?.items.map((x) => (
          <div className="record" key={x.id}>
            <strong>
              {shortTime(x.starts_at)} → {shortTime(x.ends_at)}
            </strong>
            <span>
              {x.status} ·{" "}
              {areas.data?.items.find((a) => a.id === x.location_id)?.name_bn ||
                x.location_id}
            </span>
            <div className="inline-actions">
              <button className="btn btn-sm" onClick={() => setEdit(x)}>
                সম্পাদনা
              </button>
              {x.status === "announced" && (
                <button
                  className="btn btn-sm"
                  onClick={() =>
                    action.run(() =>
                      api(`/api/admin/schedules/${x.id}/cancel`, {
                        method: "POST",
                      }),
                    )
                  }
                >
                  বাতিল চিহ্নিত
                </button>
              )}
              <button
                className="btn btn-sm btn-outline btn-error"
                onClick={() => {
                  if (window.confirm("সময়সূচি মুছবেন?"))
                    action.run(() =>
                      api(`/api/admin/schedules/${x.id}`, { method: "DELETE" }),
                    );
                }}
              >
                মুছুন
              </button>
            </div>
          </div>
        ))}
        <ErrorBox message={list.error} />
        {!list.data?.items.length && (
          <EmptyState title="সময়সূচি নেই">
            যাচাইকৃত নোটিশ ও এলাকা দরকার।
          </EmptyState>
        )}
      </Card>
    </div>
  );
}
function AdminEvents({
  version,
  reload,
}: {
  version: number;
  reload: () => void;
}) {
  const areas = useData<Page<Location>>(
      `/api/locations?page_size=100&v=${version}`,
    ),
    [area, setArea] = useState("");
  const list = useData<Page<Event>>(
    area
      ? `/api/events?location_id=${area}&page_size=100&v=${version}`
      : "/api/health/live",
  );
  const action = useAsyncAction(reload);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await action.run(() =>
      api("/api/admin/events", {
        method: "POST",
        body: JSON.stringify({
          location_id: f.get("location_id"),
          started_at: bdToIso(String(f.get("started_at"))),
          start_evidence: f.get("start_evidence"),
        }),
      }),
    );
  }
  return (
    <div className="admin-grid">
      <Card title="প্রমাণসহ বিভ্রাট রেকর্ড">
        <p className="hint">
          ব্যক্তিগত রিপোর্ট বা সময়সূচি থেকে স্বয়ংক্রিয় ঘটনা তৈরি হয় না।
        </p>
        <form className="form-stack" onSubmit={submit}>
          <AreaChooser
            items={areas.data?.items || []}
            value={area}
            onChange={setArea}
          />
          <input type="hidden" name="location_id" value={area} />
          <Field label="শুরু · বাংলাদেশ">
            <input
              name="started_at"
              type="datetime-local"
              className="input input-bordered"
              required
            />
          </Field>
          <Field label="শুরুর প্রমাণ">
            <textarea
              name="start_evidence"
              className="textarea textarea-bordered"
              minLength={12}
              required
            />
          </Field>
          <ErrorBox message={action.error} />
          <Submit busy={action.busy}>ঘটনা রেকর্ড</Submit>
        </form>
      </Card>
      <Card title="যাচাইকৃত ঘটনার তালিকা">
        {Array.isArray(list.data?.items) &&
          list.data.items.map((x) => (
            <div className="record" key={x.id}>
              <strong>
                {shortTime(x.started_at)} →{" "}
                {x.restored_at ? shortTime(x.restored_at) : "ফেরার তথ্য নেই"}
              </strong>
              <span>শুরুর প্রমাণ: {x.start_evidence}</span>
              {x.restoration_evidence && (
                <span>ফেরার প্রমাণ: {x.restoration_evidence}</span>
              )}
              {!x.restored_at && (
                <button
                  className="btn btn-sm"
                  onClick={() => {
                    const evidence = window.prompt(
                      "পুনরুদ্ধারের প্রমাণ লিখুন (কমপক্ষে ১২ অক্ষর)",
                    );
                    if (!evidence) return;
                    const time = window.prompt(
                      "ফেরার সময়, বাংলাদেশ সময় (YYYY-MM-DDTHH:mm)",
                      localInputTime(new Date()),
                    );
                    if (time)
                      action.run(() =>
                        api(`/api/admin/events/${x.id}/restore`, {
                          method: "POST",
                          body: JSON.stringify({
                            evidence,
                            restored_at: bdToIso(time),
                          }),
                        }),
                      );
                  }}
                >
                  প্রমাণ দিয়ে ফিরেছে চিহ্নিত
                </button>
              )}
            </div>
          ))}
        {!area && (
          <EmptyState title="এলাকা বাছুন">
            ঘটনা দেখতে যাচাইকৃত এলাকা নির্বাচন করুন।
          </EmptyState>
        )}
      </Card>
    </div>
  );
}
