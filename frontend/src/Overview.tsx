import { useEffect, useRef, useState } from "react";
import {
  FiArrowRight,
  FiCalendar,
  FiMapPin,
  FiRefreshCw,
  FiShield,
  FiZap,
} from "react-icons/fi";
import {
  api,
  shortTime,
  type Location,
  type Notice,
  type Page,
  type Report,
  type Schedule,
} from "./client";
import { LocationPicker } from "./components/LocationPicker";
import { Card, EmptyState, EvidenceBadge } from "./components/ui";
import { Link, useSearchParams } from "./navigation";
import { usePolling } from "./polling";
import { useSession } from "./session";

type AreaOverview = {
  area: Location;
  available: boolean;
  retrieved_at: string;
  instance_mode: "demo" | "pilot";
  schedules: {
    items: (Schedule & {
      notice: Notice;
      partial_coverage: boolean;
      window_state: string;
    })[];
    total: number;
    page: number;
    page_size: number;
  };
  community: {
    counts: Record<string, number>;
    unique_reporters: number;
    latest_observed_at: string | null;
    window_start: string;
    window_end: string;
    evidence_label: string;
  };
  recent_reports: Report[];
};
const labels: Record<string, string> = {
  power_off: "বিদ্যুৎ নেই",
  power_back: "বিদ্যুৎ ফিরেছে",
  still_off: "আমার এখনো আসেনি",
  mixed: "মিশ্র রিপোর্ট",
  interruptions_reported: "বিভ্রাটের রিপোর্ট আছে",
  restoration_reports: "বিদ্যুৎ ফেরার রিপোর্ট আছে",
  no_recent_reports: "সাম্প্রতিক পর্যবেক্ষণ নেই",
};

export function Overview() {
  const { user } = useSession();
  const [params, setParams] = useSearchParams();
  const selected = params.get("location_id") || "";
  const requestedPage = Number(params.get("page") || 1);
  const page =
    Number.isSafeInteger(requestedPage) && requestedPage >= 1
      ? requestedPage
      : 1;
  const automatic = useRef(false);
  const [selectionError, setSelectionError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const demo = process.env.NEXT_PUBLIC_DEMO_INSTANCE === "true";
  const board = usePolling<AreaOverview>(
    selected
      ? `/api/area-overview?location_id=${encodeURIComponent(selected)}&page=${page}`
      : null,
    "public",
  );
  const notices = usePolling<Page<Notice>>(
    selected ? null : "/api/notices?page_size=3",
    "public",
  );
  function choose(id: string) {
    automatic.current = true;
    setParams((old) => {
      const next = new URLSearchParams(old);
      if (id) next.set("location_id", id);
      else next.delete("location_id");
      next.delete("page");
      return next;
    });
  }
  useEffect(() => {
    if (!demo || selected || automatic.current) return;
    const controller = new AbortController();
    api<Page<Location>>(
      "/api/locations?kind=neighborhood&status=verified&page_size=1",
      { signal: controller.signal },
    )
      .then((result) => {
        if (!controller.signal.aborted && result.items[0]) {
          automatic.current = true;
          setParams((old) =>
            old.has("location_id")
              ? old
              : new URLSearchParams({ location_id: result.items[0].id }),
          );
        }
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setSelectionError(
            "ডেমো এলাকা স্বয়ংক্রিয়ভাবে লোড হয়নি। নিচে নাম দিয়ে খুঁজুন বা আবার চেষ্টা করুন।",
          );
      });
    return () => controller.abort();
  }, [demo, selected, setParams]);
  const snapshot = board.data;
  const fictional = demo || snapshot?.instance_mode === "demo";
  const target = selected ? board : notices;
  async function refresh() {
    setRefreshing(true);
    try {
      await target.refresh();
    } finally {
      setRefreshing(false);
    }
  }
  const dashboard = selected
    ? `/dashboard?location_id=${encodeURIComponent(selected)}`
    : "/dashboard";
  return (
    <>
      <section className="home-hero" aria-labelledby="home-title">
        <div>
          <p className="eyebrow">GRIDWATCH BD · বাংলাদেশ</p>
          <h1 id="home-title">
            বিদ্যুতের খবর বুঝে,
            <br />
            দিনের পরিকল্পনা করুন।
          </h1>
          <p>
            ঘোষিত সময়সূচি দেখুন, নিজের সংযোগের খবর জানান এবং কাজের সময় মিলিয়ে
            নিন। প্রতিটি তথ্যের উৎস ও সময় আলাদা করে দেখানো হয়।
          </p>
          <div className="home-actions">
            <a className="btn btn-primary" href="#area-picker">
              <FiMapPin aria-hidden="true" /> এলাকা বাছুন
            </a>
            <Link className="btn btn-outline" to={dashboard}>
              {user ? "আমার ড্যাশবোর্ড" : "প্রবেশ করে রিপোর্ট দিন"}
              <FiArrowRight aria-hidden="true" />
            </Link>
          </div>
        </div>
        <div className="home-principles">
          <FiShield aria-hidden="true" />
          <strong>তথ্যের সীমা জানুন</strong>
          <p>
            ঘোষণা একটি পরিকল্পনা। একজনের রিপোর্ট তাঁর সংযোগের খবর। রিপোর্ট না
            থাকলে এলাকার অবস্থা অজানা।
          </p>
          <Link to="/sources">উৎস ও যাচাই সম্পর্কে জানুন →</Link>
        </div>
      </section>
      <div className="home-workflows" aria-label="ব্যবহারের ধাপ">
        <Link to={dashboard}>
          <FiMapPin aria-hidden="true" />
          <strong>এলাকা ও নিজের সংযোগ</strong>
          <span>সংরক্ষণ, ডিফল্ট ও off/back রিপোর্ট</span>
        </Link>
        <Link to="/activities">
          <FiCalendar aria-hidden="true" />
          <strong>কাজের সময় মিলিয়ে নিন</strong>
          <span>ঘোষণার সঙ্গে overlap দেখুন</span>
        </Link>
        <Link to="/history">
          <FiZap aria-hidden="true" />
          <strong>নিজের ইতিহাস</strong>
          <span>জানা ও অসম্পূর্ণ সময় আলাদা</span>
        </Link>
      </div>
      <Card title="কোন এলাকার তথ্য দেখতে চান?" className="home-picker">
        <div id="area-picker" tabIndex={-1}>
          <p className="hint">
            নাম, English alias বা ID দিয়ে খুঁজুন। সরকারি প্রশাসনিক এলাকা ও
            বিদ্যুতের feeder coverage এক নয়।
          </p>
          {selectionError && <p role="status">{selectionError}</p>}
          <LocationPicker value={selected} onChange={choose} />
        </div>
      </Card>
      <section
        className="home-board"
        aria-label="নির্বাচিত এলাকার প্রকাশ্য তথ্য"
      >
        <div className="home-board-heading">
          <div>
            <p className="eyebrow">
              {fictional
                ? "কাল্পনিক অনুশীলন · বাস্তব বিদ্যুৎ তথ্য নয়"
                : "উৎসসহ প্রকাশিত তথ্য"}
            </p>
            <h2>
              {snapshot?.area.name_bn ||
                (selected ? "এলাকার তথ্য" : "প্রকাশিত সাম্প্রতিক নোটিশ")}
            </h2>
          </div>
          <button
            className="btn btn-sm btn-outline"
            onClick={() => void refresh()}
            disabled={target.loading || refreshing}
          >
            <FiRefreshCw aria-hidden="true" />{" "}
            {refreshing ? "হালনাগাদ হচ্ছে…" : "হালনাগাদ করুন"}
          </button>
        </div>
        {target.loading && (
          <p className="loading-state" role="status">
            প্রকাশিত তথ্য লোড হচ্ছে…
          </p>
        )}
        {target.error && (
          <div className="alert alert-error" role="alert">
            <span>
              তথ্য হালনাগাদ হয়নি। {target.error}{" "}
              {target.data
                ? "আগের তথ্য পুরোনো হিসেবে দেখানো হচ্ছে।"
                : "কোনো সংখ্যা ধরে নেওয়া হচ্ছে না।"}
            </span>
            <button className="btn btn-sm" onClick={() => void refresh()}>
              আবার চেষ্টা করুন
            </button>
          </div>
        )}
        {target.stale && target.data && !target.error && (
          <p role="status" className="freshness-warning">
            আগের সংগ্রহ করা তথ্য দেখানো হচ্ছে; নিচের উৎস ও পর্যবেক্ষণের সময়
            মিলিয়ে নিন।
          </p>
        )}
        {selected && snapshot && (
          <div className={board.stale ? "outdated" : ""}>
            <p className="hint">
              সর্বশেষ সফল সংগ্রহ: {shortTime(board.retrievedAt)} · পর্যবেক্ষণের
              সময় নিচে আলাদা আছে।
            </p>
            {!snapshot.available && (
              <p role="status">
                এলাকার যাচাই বর্তমানে উপলব্ধ নয়; নতুন রিপোর্টের আগে যাচাইকৃত
                এলাকা বাছুন।
              </p>
            )}
            <div className="home-evidence-grid">
              <Card title="কমিউনিটির পর্যবেক্ষণ">
                <EvidenceBadge>এলাকার বিদ্যুৎ অবস্থা: অজানা</EvidenceBadge>
                <h3>
                  {labels[snapshot.community.evidence_label] ||
                    "পর্যবেক্ষণের সারাংশ"}
                </h3>
                <p>
                  সময়ের সীমা: {shortTime(snapshot.community.window_start)} →{" "}
                  {shortTime(snapshot.community.window_end)}
                </p>
                <dl className="home-counts">
                  <div>
                    <dt>নেই / এখনো আসেনি</dt>
                    <dd>
                      {(
                        snapshot.community.counts.power_off +
                        snapshot.community.counts.still_off
                      ).toLocaleString("bn-BD")}
                    </dd>
                  </div>
                  <div>
                    <dt>ফিরেছে বলে রিপোর্ট</dt>
                    <dd>
                      {snapshot.community.counts.power_back.toLocaleString(
                        "bn-BD",
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>স্বতন্ত্র রিপোর্টকারী</dt>
                    <dd>
                      {snapshot.community.unique_reporters.toLocaleString(
                        "bn-BD",
                      )}
                    </dd>
                  </div>
                </dl>
                <p className="hint">
                  প্রতি ব্যক্তির সর্বশেষ গৃহীত পর্যবেক্ষণ একবার গণনা। সবাইকে যোগ
                  করে area-wide downtime বলা হচ্ছে না।
                </p>
                <p>
                  সর্বশেষ পর্যবেক্ষণ:{" "}
                  {snapshot.community.latest_observed_at
                    ? shortTime(snapshot.community.latest_observed_at)
                    : "সময়ের সীমায় কোনো রিপোর্ট নেই"}
                </p>
                <Link className="btn btn-primary" to={dashboard}>
                  নিজের সংযোগের খবর দিন
                </Link>
              </Card>
              <Card title="আজ ও আগামী সাত দিনের ঘোষণা">
                <p className="hint">
                  বাংলাদেশ সময়। নির্ধারিত শেষ সময় পেরোনো বিদ্যুৎ ফেরার প্রমাণ
                  নয়।
                </p>
                {!snapshot.schedules.items.length && (
                  <EmptyState title="এই সময়ে প্রকাশিত ঘোষণা নেই">
                    বিদ্যুৎ থাকার নিশ্চয়তা নয়। পুরোনো প্রকাশিত নোটিশ নোটিশ
                    পাতায় পাবেন।
                  </EmptyState>
                )}
                {snapshot.schedules.items.map((schedule) => (
                  <article className="record" key={schedule.id}>
                    <strong>{schedule.notice.title}</strong>
                    <EvidenceBadge>
                      {schedule.status === "cancelled"
                        ? "বাতিল · পরিকল্পনায় গণ্য নয়"
                        : schedule.status === "superseded"
                          ? "পরিবর্তিত ঘোষণা"
                          : schedule.window_state === "announced_window_ended"
                            ? "ঘোষিত সময় শেষ"
                            : "ঘোষিত সময়সূচি"}
                    </EvidenceBadge>
                    <p>
                      {shortTime(schedule.starts_at)} →{" "}
                      {shortTime(schedule.ends_at)}
                    </p>
                    <p>
                      {schedule.partial_coverage
                        ? "এই প্রশাসনিক এলাকার আংশিক আওতা; নিজের পাড়া মিলিয়ে নিন।"
                        : "নোটিশে এই এলাকার নাম রয়েছে।"}
                    </p>
                    <a
                      href={schedule.notice.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {schedule.notice.publisher} ·{" "}
                      {fictional ? "কাল্পনিক নমুনা উৎস" : "মূল উৎস"} ↗
                    </a>
                    <small>
                      প্রকাশ: {shortTime(schedule.notice.published_at)} ·
                      পরিবর্তন: {shortTime(schedule.updated_at)}
                    </small>
                  </article>
                ))}
                {snapshot.schedules.total > 10 && (
                  <div className="pager">
                    <button
                      className="btn btn-sm"
                      disabled={page <= 1}
                      onClick={() =>
                        setParams((old) => {
                          const n = new URLSearchParams(old);
                          n.set("page", String(page - 1));
                          return n;
                        })
                      }
                    >
                      পূর্ববর্তী ঘোষণা
                    </button>
                    <span>
                      মোট {snapshot.schedules.total.toLocaleString("bn-BD")}
                    </span>
                    <button
                      className="btn btn-sm"
                      disabled={page * 10 >= snapshot.schedules.total}
                      onClick={() =>
                        setParams((old) => {
                          const n = new URLSearchParams(old);
                          n.set("page", String(page + 1));
                          return n;
                        })
                      }
                    >
                      পরবর্তী ঘোষণা
                    </button>
                  </div>
                )}
              </Card>
            </div>
            <Card title="সর্বশেষ পাঁচটি গৃহীত পর্যবেক্ষণ">
              {!snapshot.recent_reports.length ? (
                <EmptyState title="এই এলাকায় কোনো গৃহীত রিপোর্ট নেই">
                  অনুপস্থিত রিপোর্ট থেকে বিদ্যুৎ থাকার সিদ্ধান্ত নেওয়া যায় না।
                </EmptyState>
              ) : (
                <ul className="home-report-list">
                  {snapshot.recent_reports.map((report) => (
                    <li key={report.id}>
                      <strong>{labels[report.kind] || report.kind}</strong>
                      <span>{shortTime(report.observed_at)}</span>
                      <small>
                        একজনের সংযোগ · ব্যক্তিগত পরিচয় প্রকাশিত নয়
                      </small>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        )}
        {!selected && notices.data && (
          <>
            <p className="hint">
              উপরের এলাকা বাছলে শুধু সেই এলাকার ঘোষণা ও community evidence
              দেখাবে।
            </p>
            {!notices.data.items.length && !notices.error && (
              <EmptyState title="প্রকাশিত নোটিশ যোগ হয়নি">
                যাচাইকৃত মূল উৎসসহ Admin প্রকাশ করলে এখানে দেখা যাবে। কোনো
                সরকারি live API সংযুক্ত নেই।
              </EmptyState>
            )}
            <div className="home-notices">
              {notices.data.items.map((notice) => (
                <Card key={notice.id} title={notice.title}>
                  {notice.is_demo && (
                    <EvidenceBadge>কাল্পনিক অনুশীলন</EvidenceBadge>
                  )}
                  <p>{notice.publisher}</p>
                  <p>
                    প্রকাশ: {shortTime(notice.published_at)} · পরিবর্তন:{" "}
                    {shortTime(notice.updated_at)}
                  </p>
                  <a
                    href={notice.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {demo || notice.is_demo
                      ? "কাল্পনিক নমুনা উৎস"
                      : "মূল নোটিশের উৎস"}{" "}
                    ↗
                  </a>
                </Card>
              ))}
            </div>
            <Link className="btn btn-outline" to="/notices">
              সব প্রকাশিত নোটিশ দেখুন <FiArrowRight aria-hidden="true" />
            </Link>
          </>
        )}
      </section>
    </>
  );
}
