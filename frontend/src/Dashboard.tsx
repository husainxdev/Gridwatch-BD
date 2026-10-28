import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { FiRefreshCw, FiMapPin } from "react-icons/fi";
import toast from "react-hot-toast";
import {
  api,
  shortTime,
  type Location,
  type Report,
  type Schedule,
  type Notice,
} from "./client";
import { useSession } from "./session";
import { usePolling, pollInterval } from "./polling";
import { Card, EmptyState } from "./components/ui";
import { EvidenceCard } from "./components/EvidenceCard";
import { LocationPicker } from "./components/LocationPicker";

type Saved = Location & {
  label: string;
  is_default: boolean;
  available: boolean;
};
type Episode = {
  id: string;
  started_at: string | null;
  ended_at: string | null;
  is_open: boolean;
  last_observed_at: string;
};
type PersonalReport = Report & { moderation: string; note: string };
type Snapshot = {
  area: Location;
  available: boolean;
  breadcrumb: { id: string; name_bn: string }[];
  retrieved_at: string;
  schedules: {
    items: (Schedule & {
      notice: Notice;
      window_state: string;
      partial_coverage: boolean;
    })[];
    total: number;
    page: number;
    from: string;
    until: string;
  };
  community: {
    counts: Record<string, number>;
    unique_reporters: number;
    evidence_label: string;
    window_start: string;
    window_end: string;
    latest_observed_at: string | null;
    retrieved_at: string;
  };
  personal: {
    latest_report: PersonalReport | null;
    episode: Episode | null;
    recent: PersonalReport[];
    history: Episode[];
  };
};
const viewing = new Map<string, string>();
window.addEventListener("gridwatch-session-ended", () => viewing.clear());
const kinds: Record<string, string> = {
  power_off: "বিদ্যুৎ নেই",
  power_back: "বিদ্যুৎ ফিরেছে",
  still_off: "আমার এখনো আসেনি",
};
const communityLabels: Record<string, string> = {
  no_recent_reports: "সাম্প্রতিক রিপোর্ট নেই",
  interruptions_reported: "বিভ্রাটের রিপোর্ট আছে",
  mixed: "মিশ্র রিপোর্ট — কারও ফিরেছে, কারও নেই",
  restoration_reports: "বিদ্যুৎ ফেরার রিপোর্ট এসেছে",
};
function elapsed(episode: Episode, clock: number) {
  if (!episode.started_at) return "শুরুর সময় অজানা";
  const seconds = Math.max(
    0,
    Math.floor(
      ((episode.ended_at ? Date.parse(episode.ended_at) : clock) -
        Date.parse(episode.started_at)) /
        1000,
    ),
  );
  const minutes = Math.floor(seconds / 60);
  return `${Math.floor(minutes / 60).toLocaleString("bn-BD")} ঘণ্টা ${(minutes % 60).toLocaleString("bn-BD")} মিনিট`;
}
function SavedItem({
  area,
  select,
  run,
  busy,
}: {
  area: Saved;
  select: () => void;
  run: (fn: () => Promise<unknown>, message: string) => Promise<void>;
  busy: boolean;
}) {
  const [label, setLabel] = useState(area.label);
  useEffect(() => setLabel(area.label), [area.label]);
  return (
    <div className="saved-area">
      <button
        type="button"
        className="btn saved-switch"
        onClick={select}
        disabled={!area.available}
      >
        <FiMapPin aria-hidden="true" />
        {area.label ? `${area.label} · ` : ""}
        {area.name_bn}
        {area.is_default ? " · ডিফল্ট" : ""}
      </button>
      {!area.available && (
        <p role="status">এলাকাটি এখন যাচাইকৃত নয়; অন্য এলাকা নিজে বাছুন।</p>
      )}
      <form
        className="saved-controls"
        onSubmit={(e) => {
          e.preventDefault();
          void run(
            () =>
              api(`/api/saved-areas/${area.id}`, {
                method: "PUT",
                body: JSON.stringify({ label, is_default: area.is_default }),
              }),
            "লেবেল সংরক্ষিত",
          );
        }}
      >
        <label className="field">
          এলাকার সংক্ষিপ্ত নাম
          <input
            className="input input-bordered"
            maxLength={60}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="বাসা / বিশ্ববিদ্যালয়"
          />
        </label>
        <div className="inline-actions">
          <button className="btn btn-sm" disabled={busy}>
            লেবেল সংরক্ষণ
          </button>
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy || !area.available}
            onClick={() =>
              void run(
                () =>
                  api(`/api/saved-areas/${area.id}`, {
                    method: "PUT",
                    body: JSON.stringify({
                      label,
                      is_default: !area.is_default,
                    }),
                  }),
                area.is_default
                  ? "ডিফল্ট সরানো হয়েছে"
                  : "ডিফল্ট এলাকা সংরক্ষিত",
              )
            }
          >
            {area.is_default ? "ডিফল্ট সরান" : "ডিফল্ট করুন"}
          </button>
          <button
            type="button"
            className="btn btn-sm"
            disabled={busy}
            onClick={() =>
              void run(
                () => api(`/api/saved-areas/${area.id}`, { method: "DELETE" }),
                "সংরক্ষিত এলাকা সরানো হয়েছে",
              )
            }
          >
            সরান
          </button>
        </div>
      </form>
    </div>
  );
}
export function DashboardView({
  renderExtra,
}: {
  renderExtra: (id: string) => ReactNode;
}) {
  const { user } = useSession();
  const uid = user!.id;
  const [selected, updateSelected] = useState(viewing.get(uid) || ""),
    [page, setPage] = useState(1),
    [actionError, setActionError] = useState(""),
    [busy, setBusy] = useState(false),
    [note, setNote] = useState(""),
    [fallback, setFallback] = useState("");
  const initialized = useRef(false),
    mounted = useRef(true),
    currentArea = useRef(selected);
  currentArea.current = selected;
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const saved = usePolling<{ items: Saved[] }>("/api/saved-areas", uid);
  const dashboard = usePolling<Snapshot>(
    selected ? `/api/dashboard?location_id=${selected}&page=${page}` : null,
    uid,
  );
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    const tick = () => {
      if (!document.hidden) setClock(Date.now());
    };
    const timer = setInterval(tick, 1000);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, []);
  function choose(id: string) {
    initialized.current = true;
    viewing.set(uid, id);
    updateSelected(id);
    setPage(1);
    setActionError("");
    setFallback("");
  }
  useEffect(() => {
    if (!saved.data || initialized.current) return;
    initialized.current = true;
    if (!selected) {
      const first = saved.data.items.find((x) => x.is_default);
      if (first?.available) choose(first.id);
      else if (first)
        setFallback(
          "আপনার ডিফল্ট এলাকাটি এখন উপলব্ধ নয়। নিজে একটি যাচাইকৃত এলাকা বাছুন।",
        );
    }
  }, [saved.data]); // Initialize once: temporary viewing never changes the saved default.
  const savedBefore = useRef<Saved[]>([]);
  useEffect(() => {
    if (!saved.data) return;
    const before = savedBefore.current;
    const removed =
      before.some((x) => x.id === selected) &&
      !saved.data.items.some((x) => x.id === selected);
    const unavailable =
      saved.data.items.find((x) => x.id === selected)?.available === false;
    if (removed || unavailable) {
      choose("");
      setFallback(
        removed
          ? "নির্বাচিত সংরক্ষিত এলাকাটি সরানো হয়েছে। নতুন এলাকা নিজে বাছুন।"
          : "নির্বাচিত এলাকাটি এখন যাচাইকৃত নয়। অন্য এলাকা নিজে বাছুন।",
      );
    }
    savedBefore.current = saved.data.items;
  }, [saved.data, selected]);
  const data = dashboard.data;
  useEffect(() => {
    if (dashboard.status === 404 || data?.available === false) {
      choose("");
      setFallback(
        "নির্বাচিত এলাকাটি এখন পাওয়া যাচ্ছে না বা যাচাইকৃত নয়। অন্য এলাকা নিজে বাছুন।",
      );
    }
  }, [dashboard.status, data?.available]);
  const available = !!selected && data?.available === true && !dashboard.error;
  type Payload = {
    location_id: string;
    kind: string;
    observed_at: string;
    idempotency_key: string;
    note: string;
  };
  const [pending, setPending] = useState<Payload | null>(null);
  async function run(fn: () => Promise<unknown>, message: string) {
    setBusy(true);
    setActionError("");
    try {
      const r = await fn();
      if (!mounted.current) return;
      if (r && typeof r === "object" && "already_saved" in r && r.already_saved)
        toast("এলাকাটি আগে থেকেই সংরক্ষিত");
      else toast.success(message);
      await saved.refresh();
    } catch (e) {
      if (mounted.current) setActionError((e as Error).message);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  async function report(kind: string) {
    if (!available || busy) return;
    const target = selected;
    const body =
      pending?.location_id === target && pending.kind === kind
        ? pending
        : {
            location_id: target,
            kind,
            observed_at: new Date().toISOString(),
            idempotency_key: crypto.randomUUID(),
            note,
          };
    setPending(body);
    setBusy(true);
    setActionError("");
    try {
      await api("/api/reports", { method: "POST", body: JSON.stringify(body) });
      if (!mounted.current || currentArea.current !== target) return;
      setPending(null);
      setNote("");
      toast.success("আপনার সংযোগের রিপোর্ট জমা হয়েছে");
      await dashboard.refresh();
    } catch (e) {
      if (mounted.current && currentArea.current === target)
        setActionError((e as Error).message);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  const stale = dashboard.stale;
  const episode = data?.personal.episode;
  const own = data?.personal.latest_report;
  const showMixed = episode?.is_open && !!data?.community.counts.power_back;
  const savedSelected = saved.data?.items.find((x) => x.id === selected);
  return (
    <>
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">আপনার এলাকা · আপনার সংযোগ</p>
          <h1>স্বাগতম, {user?.display_name}</h1>
          <p className="hint">
            ঘোষিত পরিকল্পনা, প্রতিবেশীদের পর্যবেক্ষণ ও আপনার ব্যক্তিগত অবস্থা
            আলাদা করে দেখুন। সময় বাংলাদেশ (UTC+6)।
          </p>
        </div>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => {
            void saved.refresh();
            void dashboard.refresh();
          }}
        >
          <FiRefreshCw aria-hidden="true" />
          রিপোর্ট ও ইতিহাস রিফ্রেশ
        </button>
      </div>
      <Card title="এলাকা নির্বাচন">
        <p>
          এলাকা বাছলে ঘোষিত সময়সূচি ও সাম্প্রতিক রিপোর্ট দেখতে এবং নিজের
          সংযোগের খবর দিতে পারবেন। দেখা, সংরক্ষণ ও ডিফল্ট করা আলাদা কাজ।
        </p>
        <LocationPicker value={selected} onChange={choose} />
        {fallback && (
          <p className="alert" role="status">
            {fallback}
          </p>
        )}
        {data && (
          <div className="selected-area">
            <strong>দেখছেন: {data.area.name_bn}</strong>
            <p>{data.breadcrumb.map((x) => x.name_bn).join(" / ")}</p>
            {!data.available && (
              <p role="alert">
                এলাকাটির যাচাই এখন বাকি। রিপোর্ট বন্ধ আছে; অন্য যাচাইকৃত এলাকা
                বাছুন।
              </p>
            )}
            <button
              type="button"
              className="btn btn-sm"
              disabled={!available || busy}
              onClick={() =>
                void run(
                  () => api(`/api/saved-areas/${selected}`, { method: "POST" }),
                  "এলাকা সংরক্ষিত",
                )
              }
            >
              এলাকা সংরক্ষণ
            </button>
            {savedSelected && (
              <span>
                সংরক্ষিত{savedSelected.is_default ? " · আপনার ডিফল্ট" : ""}
              </span>
            )}
          </div>
        )}
        {!selected && (
          <EmptyState title="একটি যাচাইকৃত এলাকা বাছুন">
            এলাকা না থাকলে অ্যাডমিনকে মূল উৎস দিয়ে পাইলট এলাকা যাচাই করতে হবে।
            নমুনা এলাকা এখানে আসে না।
          </EmptyState>
        )}
      </Card>
      {(actionError || saved.error || dashboard.error) && (
        <div className="alert alert-error section-gap" role="alert">
          {actionError || dashboard.error || saved.error}
          {(data || saved.data) &&
            " — পুরোনো তথ্য থাকতে পারে; শূন্য ধরে নেবেন না।"}
        </div>
      )}
      {selected && dashboard.loading && !data && (
        <div role="status" className="loading-state">
          নির্বাচিত এলাকার তথ্য লোড হচ্ছে…
        </div>
      )}
      {data && (
        <>
          <div className="freshness-bar">
            <span>
              সর্বশেষ সফল সংগ্রহ:{" "}
              {dashboard.retrievedAt
                ? shortTime(dashboard.retrievedAt)
                : "অজানা"}
            </span>
            <span>
              প্রায় {Math.round(pollInterval / 1000).toLocaleString("bn-BD")}{" "}
              সেকেন্ড পরপর রিপোর্ট হালনাগাদ; তাৎক্ষণিক সেন্সর তথ্য নয়।
            </span>
            {stale && <strong role="status">পুরোনো / হালনাগাদ অনুপলব্ধ</strong>}
          </div>
          <div className="dashboard-evidence-grid">
            <EvidenceCard
              title="আমার সংযোগ"
              type="ব্যক্তিগত রিপোর্ট"
              publisher="আপনার নিজের পর্যবেক্ষণ"
              observedAt={own?.observed_at}
              updatedAt={own?.created_at}
              updateLabel="আপনার রিপোর্ট জমার সময়"
              retrievedAt={dashboard.retrievedAt}
              scope="শুধু আপনার সংযোগ; এলাকার সামগ্রিক সিদ্ধান্ত নয়।"
              stale={stale}
            >
              {own && (
                <p className="hint">
                  আপনার সর্বশেষ পর্যবেক্ষণ: {shortTime(own.observed_at)}
                </p>
              )}
              <p className="personal-state">
                {own ? kinds[own.kind] : "আপনার গৃহীত রিপোর্ট নেই"}
              </p>
              {episode && (
                <div className="episode-timer">
                  <p>
                    {episode.is_open
                      ? "আপনার বিভ্রাট এখনো বন্ধ করা হয়নি"
                      : "আপনার ব্যক্তিগত পুনঃসংযোগ রেকর্ড হয়েছে"}
                  </p>
                  <strong data-testid="episode-duration">
                    {elapsed(episode, clock)}
                  </strong>
                  <p>
                    {episode.started_at
                      ? `আপনার রিপোর্ট করা শুরু থেকে · ${shortTime(episode.started_at)}`
                      : "শুরুর সময় অজানা — সময়কাল অনুমান করা হয়নি।"}
                  </p>
                  {episode.ended_at && (
                    <p>
                      আপনার বিদ্যুৎ ফেরার পর্যবেক্ষণ:{" "}
                      {shortTime(episode.ended_at)}
                    </p>
                  )}
                </div>
              )}
              {showMixed && (
                <p className="mixed-evidence" role="status">
                  অন্যদের বিদ্যুৎ ফেরার রিপোর্ট এসেছে, আপনার বিভ্রাট এখনো খোলা।
                  আপনার সংযোগের খবর দিন; এতে গৃহস্থালি ত্রুটি নির্ণয় করা হচ্ছে
                  না।
                </p>
              )}
              <p className="hint">
                বিদ্যুৎ ফেরার আনুমানিক সময় দেওয়া নেই। ঘোষিত শেষ সময়
                পুনঃসংযোগের নিশ্চয়তা নয়।
              </p>
              <label className="field">
                ব্যক্তিগত মন্তব্য (ঐচ্ছিক)
                <input
                  className="input input-bordered"
                  maxLength={500}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </label>
              <div className="report-actions">
                {Object.entries(kinds).map(([kind, label]) => (
                  <button
                    type="button"
                    className={`btn ${kind === "power_off" ? "btn-primary" : ""}`}
                    key={kind}
                    disabled={busy || !available}
                    onClick={() => void report(kind)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {!episode?.is_open && (
                <p className="hint">
                  “আমার এখনো আসেনি” দিলে নতুন বর্তমান পর্যবেক্ষণ জমা হবে; শুরুর
                  সময় অজানা থাকবে।
                </p>
              )}
              {pending?.location_id === selected && (
                <p className="hint">
                  একই বোতাম আবার চাপলে আগের অনুরোধ একই key দিয়ে পাঠানো হবে।
                </p>
              )}
            </EvidenceCard>
            <EvidenceCard
              title="এলাকার সাম্প্রতিক পর্যবেক্ষণ"
              type="কমিউনিটির রিপোর্ট"
              publisher="স্বতন্ত্র ব্যবহারকারীদের ব্যক্তিগত সংযোগের পর্যবেক্ষণ"
              observedAt={data.community.latest_observed_at}
              updatedAt={data.community.latest_observed_at}
              updateLabel="সর্বশেষ প্রযোজ্য পর্যবেক্ষণ"
              retrievedAt={dashboard.retrievedAt}
              scope="প্রতি ব্যক্তির সর্বশেষ গৃহীত পর্যবেক্ষণ; এটি সরকারি বা এলাকা জুড়ে নিশ্চিত অবস্থা নয়।"
              stale={stale}
            >
              <h3>{communityLabels[data.community.evidence_label]}</h3>
              <p data-testid="unique-reporters">
                স্বতন্ত্র সাম্প্রতিক রিপোর্টকারী:{" "}
                {data.community.unique_reporters.toLocaleString("bn-BD")}
              </p>
              <ul className="community-counts">
                {Object.entries(kinds).map(([kind, label]) => (
                  <li key={kind}>
                    {label}:{" "}
                    {data.community.counts[kind].toLocaleString("bn-BD")}
                  </li>
                ))}
              </ul>
              <p>
                পর্যবেক্ষণের সময়সীমা: {shortTime(data.community.window_start)}{" "}
                → {shortTime(data.community.window_end)}
              </p>
              <p>
                সর্বশেষ প্রযোজ্য পর্যবেক্ষণ:{" "}
                {data.community.latest_observed_at
                  ? shortTime(data.community.latest_observed_at)
                  : "সাম্প্রতিক তথ্য নেই"}
              </p>
              <p className="hint">
                রিপোর্ট না থাকা বিদ্যুৎ থাকার প্রমাণ নয়। কারও বিদ্যুৎ ফেরার খবর
                আপনার ব্যক্তিগত বিভ্রাট বন্ধ করে না।
              </p>
            </EvidenceCard>
          </div>
          <section
            className="section-gap"
            aria-label="নির্বাচিত এলাকার ঘোষিত সময়সূচি"
          >
            <h2>আজ ও আগামী সাত দিনের ঘোষিত সময়সূচি</h2>
            <p>
              পরিকল্পিত সময়; বাস্তবে বিদ্যুৎ বন্ধ বা ফেরার প্রমাণ নয়। যাচাইকৃত
              feeder mapping সংযুক্ত নেই।
            </p>
            {!data.schedules.items.length ? (
              <EmptyState title="এই এলাকার কোনো প্রকাশিত বিভ্রাটের সময়সূচি পাওয়া যায়নি">
                বিদ্যুৎ থাকবে—এমন নিশ্চয়তা এতে নেই।
              </EmptyState>
            ) : (
              data.schedules.items.map((s) => {
                const status =
                  s.status === "cancelled"
                    ? "বাতিল"
                    : s.status === "superseded"
                      ? "সংশোধিত"
                      : clock < Date.parse(s.starts_at)
                        ? "আসন্ন ঘোষিত বিভ্রাট"
                        : clock < Date.parse(s.ends_at)
                          ? "ঘোষিত সময়ের মধ্যে"
                          : "ঘোষিত সময় শেষ";
                return (
                  <EvidenceCard
                    key={s.id}
                    title={s.notice.title}
                    type="ঘোষিত সময়সূচি"
                    publisher={s.notice.publisher}
                    source={s.notice.source_url}
                    verification="GridWatch Admin উৎস পর্যালোচনা করেছেন; কর্তৃপক্ষের প্রতিনিধি বা সরকারি অনুমোদন বোঝায় না।"
                    observedAt={s.notice.published_at}
                    updatedAt={s.notice.updated_at}
                    retrievedAt={dashboard.retrievedAt}
                    stale={stale}
                    scope={`${s.coverage_scope === "named_locations" ? "শুধু নামযুক্ত এলাকা; পুরো এলাকা ধরে নেওয়া হয়নি" : "মূল ঘোষণায় সমগ্র নির্বাচিত প্রশাসনিক এলাকার আওতা"} · ${s.coverage.map((x) => x.name_bn).join(" / ")}`}
                  >
                    <strong className="schedule-state">{status}</strong>
                    {s.partial_coverage && (
                      <p className="mixed-evidence">
                        নির্বাচিত এলাকার শুধু নামযুক্ত অংশে প্রযোজ্য — পুরো
                        এলাকার ঘোষণা নয়। প্রকাশের সময়কার প্রশাসনিক সম্পর্ক
                        অনুযায়ী দেখানো হচ্ছে।
                      </p>
                    )}
                    <p>
                      {shortTime(s.starts_at)} → {shortTime(s.ends_at)}
                    </p>
                    <p>
                      কারণ: {s.category} · সংস্করণ {s.version}
                    </p>
                    <p>সময়সূচির পরিবর্তন: {shortTime(s.updated_at)}</p>
                    <details>
                      <summary>মূল নোটিশ ও সীমাবদ্ধতা</summary>
                      <p>
                        মূল প্রকাশক: {s.notice.publisher}। বিদ্যুৎ ফেরার
                        আনুমানিক সময় দেওয়া নেই; ঘোষিত শেষ সময় প্রকৃত
                        পুনঃসংযোগের সময় নয়।
                      </p>
                      <a
                        href={s.notice.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        সম্পূর্ণ মূল নোটিশ ↗
                      </a>
                    </details>
                  </EvidenceCard>
                );
              })
            )}
            <div className="pager">
              <button
                type="button"
                className="btn btn-sm"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                আগের সময়সূচি
              </button>
              <span>
                পৃষ্ঠা {page} · মোট{" "}
                {data.schedules.total.toLocaleString("bn-BD")}টি
              </span>
              <button
                type="button"
                className="btn btn-sm"
                disabled={page * 10 >= data.schedules.total}
                onClick={() => setPage(page + 1)}
              >
                পরের সময়সূচি
              </button>
              <Link to="/notices">সব নোটিশ</Link>
            </div>
          </section>
          <Card title="আমার সাম্প্রতিক কার্যকলাপ" className="section-gap">
            {data.personal.recent.length ? (
              data.personal.recent.map((r) => (
                <div className="record" key={r.id}>
                  <strong>{kinds[r.kind]}</strong>
                  <span>
                    {shortTime(r.observed_at)} ·{" "}
                    {r.moderation === "accepted"
                      ? "গৃহীত ব্যক্তিগত পর্যবেক্ষণ"
                      : r.moderation === "pending"
                        ? "পর্যালোচনাধীন"
                        : "সারাংশ থেকে বাদ"}
                  </span>
                  {r.note && <p>{r.note}</p>}
                </div>
              ))
            ) : (
              <p>এই এলাকায় নিজের কোনো রিপোর্ট নেই।</p>
            )}
            <h3>আমার সংযোগের বিভ্রাট ইতিহাস</h3>
            {data.personal.history.map((e) => (
              <p key={e.id}>
                {e.started_at ? shortTime(e.started_at) : "শুরুর সময় অজানা"} →{" "}
                {e.ended_at
                  ? shortTime(e.ended_at)
                  : "পুনঃসংযোগের সময় দেওয়া নেই"}{" "}
                ·{" "}
                {e.started_at && e.ended_at
                  ? elapsed(e, clock)
                  : "সম্পূর্ণ সময়কাল অজানা"}
              </p>
            ))}
            <p className="hint">
              এটি আপনার নির্বাচিত এলাকার সর্বশেষ পাঁচটি কার্যকলাপ। অন্যের পরিচয়
              দেখানো হয় না।
            </p>
          </Card>
          <details className="section-gap">
            <summary>
              আমার সংযোগের বিভ্রাট ইতিহাস ও কাজের সময় মিলিয়ে দেখা
            </summary>
            <p>
              উপরের ব্যক্তিগত timer সর্বশেষ প্রাসঙ্গিক episode দেখায়; পুরোনো
              রিপোর্টে কোনো পরিবর্তন করা হয়নি।
            </p>
            {renderExtra(selected)}
          </details>
        </>
      )}
      <Card title="সংরক্ষিত এলাকা" className="section-gap">
        {saved.loading && !saved.data ? (
          <p role="status">সংরক্ষিত এলাকা লোড হচ্ছে…</p>
        ) : saved.data?.items.length ? (
          saved.data.items.map((x) => (
            <SavedItem
              key={x.id}
              area={x}
              select={() => choose(x.id)}
              run={run}
              busy={busy}
            />
          ))
        ) : saved.error ? (
          <p>সংরক্ষিত তালিকা এখন পাওয়া যাচ্ছে না।</p>
        ) : (
          <EmptyState title="এখনো সংরক্ষিত এলাকা নেই">
            এলাকা বেছে সংরক্ষণ করুন। ডিফল্ট ও লেবেল আপনার account-এ সংরক্ষিত
            থাকবে।
          </EmptyState>
        )}
        {saved.stale && saved.data && (
          <p role="status">সংরক্ষিত তালিকাটি পুরোনো হতে পারে।</p>
        )}
      </Card>
    </>
  );
}
