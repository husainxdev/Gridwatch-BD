import { RegistryWorkspace } from "./Registry";
import {
  NoticeSelector,
  AdminOverview,
  AdminAudit,
  AuditTrail,
  ListControls,
  ModerationWorkspace,
  OfficeDirectory,
  useList,
} from "./management";
import { DashboardView } from "./Dashboard";
import { PublicationActions, PublishedSchedules } from "./evidence-ui";
import { LocationPicker } from "./components/LocationPicker";
import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "./navigation";
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
    const controller = new AbortController();
    setLoading(true);
    setData(null);
    setError("");
    api<T>(path, { signal: controller.signal })
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
      controller.abort();
    };
  }, [path, version]);
  return { data, error, loading, reload: () => setVersion((x) => x + 1) };
}
function useAsyncAction(reload?: () => void) {
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function run(
    action: () => Promise<unknown>,
    success = "সংরক্ষণ হয়েছে",
  ) {
    if (inFlight.current) return false;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await action();
      toast.success(success);
      if (
        result &&
        typeof result === "object" &&
        "warning" in result &&
        result.warning
      )
        toast(String(result.warning));
      reload?.();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      inFlight.current = false;
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
  const { user, checking, signIn, signUp } = useSession();
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
  if (checking && (mode === "login" || mode === "register"))
    return <div className="loading-state">সেশন যাচাই হচ্ছে…</div>;
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
  return <Fragment key={user.id}>{children}</Fragment>;
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
  return (
    <DashboardView
      key={user!.id}
      renderExtra={(id) => <Activity areaId={id} />}
    />
  );
}
function Activity({ areaId }: { areaId: string }) {
  return (
    <Card title="কাজের সময় ও ব্যক্তিগত ইতিহাস">
      <p>
        সংরক্ষিত কাজের সঙ্গে বর্তমান ঘোষণা মিলিয়ে দেখুন। ব্যক্তিগত ইতিহাসে শুধু
        আপনার গৃহীত পর্যবেক্ষণ থাকে।
      </p>
      <div className="inline-actions">
        <Link className="btn" to={`/activities?location_id=${areaId}`}>
          কাজের সময় মিলিয়ে দেখুন
        </Link>
        <Link className="btn" to={`/history?location_id=${areaId}`}>
          সম্পূর্ণ ব্যক্তিগত ইতিহাস
        </Link>
      </div>
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
      <PublishedSchedules />
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
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "overview";
  const setTab = (tab: string) => setParams({ tab });
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
            ["overview", "সারাংশ"],
            ["areas", "এলাকা"],
            ["reports", "রিপোর্ট"],
            ["offices", "বিদ্যুৎ অফিস"],
            ["mappings", "Feeder mapping"],
            ["publishers", "নোটিশ প্রকাশক"],
            ["audit", "পরিবর্তনের ইতিহাস"],
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
      {tab === "overview" && <AdminOverview />}
      {tab === "reports" && <ModerationWorkspace />}
      {tab === "offices" && (
        <RegistryWorkspace key="offices" entity="offices" />
      )}
      {tab === "mappings" && (
        <RegistryWorkspace key="mappings" entity="mappings" />
      )}
      {tab === "publishers" && <OfficeDirectory />}
      {tab === "audit" && <AdminAudit />}
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
  const list = useList<Location>("/api/admin/list/locations", version);
  const action = useAsyncAction(reload);
  const [edit, setEdit] = useState<Location | null>(null);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      body = {
        version: edit?.version || 1,
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
        <ListControls
          list={list}
          statuses={["verified", "unverified"]}
          kinds={[
            "division",
            "district",
            "city_corporation",
            "upazila",
            "ward",
            "union",
            "village",
            "neighborhood",
          ]}
          location
        />
        <ErrorBox message={list.error} />
        {list.data?.items.map((x) => (
          <div className="record" key={x.id}>
            <strong>
              {x.name_bn} · {x.kind}
            </strong>
            <span>
              {x.verification_status} · {x.slug}
            </span>
            <AuditTrail entity="locations" id={x.id} />
            <div className="inline-actions">
              <button
                className="btn btn-sm"
                disabled={action.busy}
                onClick={() => setEdit(x)}
              >
                সম্পাদনা
              </button>
              {x.verification_status === "verified" && (
                <button
                  disabled={action.busy}
                  className="btn btn-sm"
                  onClick={() => {
                    const reason = window.prompt(
                      "এলাকার যাচাই স্থগিতের কারণ (কমপক্ষে ৫ অক্ষর)। ইতিহাস থাকবে, সংশ্লিষ্ট ঘোষণা superseded হবে।",
                    );
                    if (
                      reason &&
                      reason.trim().length >= 5 &&
                      confirm("এই এলাকা নতুন selection-এর জন্য অনুপলব্ধ করবেন?")
                    )
                      action.run(() =>
                        api(`/api/admin/locations/${x.id}/deactivate`, {
                          method: "POST",
                          body: JSON.stringify({ version: x.version, reason }),
                        }),
                      );
                  }}
                >
                  যাচাই স্থগিত
                </button>
              )}
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
                          body: JSON.stringify({
                            source_url: url,
                            version: x.version,
                          }),
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
                  if (
                    window.confirm(
                      "অব্যবহৃত এলাকা স্থায়ীভাবে মুছবেন? সংযুক্ত রেকর্ড থাকলে মুছতে দেওয়া হবে না।",
                    )
                  )
                    action.run(() =>
                      api(`/api/admin/locations/${x.id}?version=${x.version}`, {
                        method: "DELETE",
                      }),
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
  const list = useList<Notice>("/api/admin/list/notices", version);
  const action = useAsyncAction(reload),
    [edit, setEdit] = useState<Notice | null>(null);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      version: edit?.version || 1,
      title: f.get("title"),
      body: f.get("body"),
      source_url: f.get("source_url"),
      publisher: f.get("publisher"),
      published_at: f.get("published_at")
        ? bdToIso(String(f.get("published_at")))
        : null,
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
                edit && edit.published_at
                  ? localInputTime(new Date(edit.published_at))
                  : localInputTime(new Date())
              }
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
        <ListControls
          list={list}
          statuses={["draft", "published", "withdrawn", "archived"]}
          location
          office
          category
        />
        {list.data?.items.map((x) => (
          <div className="record" key={x.id}>
            <strong>{x.title}</strong>
            <span>
              {x.verification_status} · {shortTime(x.published_at)}
            </span>
            <PublicationActions kind="notices" item={x} reload={reload} />
            <AuditTrail entity="notices" id={x.id} />
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
                        body: JSON.stringify({ version: x.version }),
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
                  if (
                    window.confirm(
                      "শুধু অব্যবহৃত খসড়া স্থায়ীভাবে মুছবেন? প্রকাশিত নোটিশ archive করুন।",
                    )
                  )
                    action.run(() =>
                      api(`/api/admin/notices/${x.id}?version=${x.version}`, {
                        method: "DELETE",
                      }),
                    );
                }}
              >
                মুছুন
              </button>
            </div>
          </div>
        ))}
        <ErrorBox message={list.error} />
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
  const list = useList<Schedule>("/api/admin/list/schedules", version);
  const [noticeId, setNoticeId] = useState("");
  const action = useAsyncAction(reload),
    [edit, setEdit] = useState<Schedule | null>(null);
  const [coverage, setCoverage] = useState<{ id: string; name_bn: string }[]>(
    [],
  );
  const [picked, setPicked] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      version: edit?.version || 1,
      category: f.get("category"),
      location_ids: coverage.map((x) => x.id),
      coverage_scope: f.get("coverage_scope"),
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
          <NoticeSelector value={noticeId} onChange={setNoticeId} />
          <LocationPicker
            value={picked}
            onChange={(id) => {
              setPicked(id);
              if (id)
                api<Location>(`/api/locations/${id}`)
                  .then((loc) =>
                    setCoverage((old) =>
                      old.some((x) => x.id === id) ? old : [...old, loc],
                    ),
                  )
                  .catch((e) => toast.error(e.message));
            }}
          />
          <input
            type="hidden"
            name="location_id"
            value={coverage[0]?.id || edit?.location_id || ""}
          />
          {coverage.map((x) => (
            <button
              key={x.id}
              type="button"
              className="btn btn-sm"
              onClick={() => setCoverage(coverage.filter((y) => y.id !== x.id))}
            >
              {x.name_bn} ×
            </button>
          ))}
          <Field label="কারণ / বিভাগ">
            <input
              name="category"
              className="input"
              defaultValue={edit?.category || "maintenance"}
              required
            />
          </Field>
          <Field label="ঘোষিত আওতা">
            <select
              name="coverage_scope"
              className="select"
              defaultValue={edit?.coverage_scope || "named_locations"}
            >
              <option value="named_locations">শুধু নামযুক্ত এলাকাসমূহ</option>
              <option value="entire_administrative_area">
                সমগ্র নির্বাচিত প্রশাসনিক এলাকা (মূল উৎস অনুসারে)
              </option>
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
        <ListControls
          list={list}
          statuses={[
            "draft",
            "published",
            "cancelled",
            "superseded",
            "archived",
          ]}
          location
          office
          category
        />
        {list.data?.items.map((x) => (
          <div className="record" key={x.id}>
            <strong>
              {shortTime(x.starts_at)} → {shortTime(x.ends_at)}
            </strong>
            <span>
              {x.status} · {x.lifecycle} · {x.location_name || x.location_id}
            </span>
            <PublicationActions kind="schedules" item={x} reload={reload} />
            <AuditTrail entity="schedules" id={x.id} />
            <div className="inline-actions">
              <button
                className="btn btn-sm"
                onClick={() => {
                  setEdit(x);
                  setNoticeId(x.notice_id);
                  setCoverage(x.coverage || []);
                  setPicked("");
                }}
              >
                সম্পাদনা
              </button>
              <button
                className="btn btn-sm btn-outline btn-error"
                onClick={() => {
                  if (
                    window.confirm(
                      "শুধু অপ্রকাশিত খসড়া মুছবেন? প্রকাশিত সময়সূচি বাতিল বা archive করুন।",
                    )
                  )
                    action.run(() =>
                      api(`/api/admin/schedules/${x.id}?version=${x.version}`, {
                        method: "DELETE",
                      }),
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
  const list = useList<Event>("/api/admin/list/events", version);
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
        <ListControls list={list} statuses={["open", "completed"]} location />
        {Array.isArray(list.data?.items) &&
          list.data.items.map((x) => (
            <div className="record" key={x.id}>
              <strong>
                {shortTime(x.started_at)} →{" "}
                {x.restored_at ? shortTime(x.restored_at) : "ফেরার তথ্য নেই"}
              </strong>
              <span>শুরুর প্রমাণ: {x.start_evidence}</span>
              <AuditTrail entity="outage_events" id={x.id} />
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
                            version: x.version,
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
      </Card>
    </div>
  );
}
