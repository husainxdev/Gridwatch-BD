import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  FiArrowRight,
  FiArrowLeft,
  FiMapPin,
  FiSearch,
  FiX,
  FiChevronRight,
  FiExternalLink,
  FiInfo,
  FiRefreshCw,
  FiLayers,
  FiCheckCircle,
} from "react-icons/fi";
import { api, ApiError, type Page } from "./client";
import { Link, useSearchParams } from "./navigation";

export type DirectoryPlace = {
  id: string;
  parent_id: string | null;
  branch: string;
  name_bn: string | null;
  name_en: string | null;
  kind: string;
  source_url: string;
  review_status: string;
  reportable: boolean;
  location_id: string | null;
  children_count: number;
  ancestors: { id: string; name: string; kind: string }[];
  census_year: number | null;
  pdf_page_claimed: number | null;
  bbs_code_segments: string | null;
};
type Summary = {
  available: boolean;
  counts: Record<string, number>;
  sources: { id: string; url: string; title: string; scope: string }[];
};
const labels: Record<string, string> = {
  division: "বিভাগ",
  district: "জেলা",
  upazila: "উপজেলা",
  city_corporation: "সিটি কর্পোরেশন",
  union: "ইউনিয়ন",
  ward: "ওয়ার্ড",
  census_thana: "জনশুমারির থানা",
  ward_segment: "জনশুমারির ওয়ার্ড অংশ",
  mauza_segment: "মৌজা / মহল্লার অংশ",
  mahalla: "মহল্লা",
  village: "গ্রাম",
  municipality: "পৌরসভা",
  cantonment: "ক্যান্টনমেন্ট",
};
const number = (value: number) => value.toLocaleString("bn-BD");
const name = (place: DirectoryPlace) =>
  place.name_bn || place.name_en || "এলাকা";

export function AreaDirectory() {
  const [params, setParams] = useSearchParams();
  const branch = ["portal", "census2022"].includes(params.get("branch") || "")
    ? params.get("branch")!
    : "all";
  const parent = params.get("parent") || "";
  const search = params.get("search") || "";
  const kind = params.get("kind") || "";
  const requested = Number(params.get("page") || 1);
  const page =
    Number.isSafeInteger(requested) && requested >= 1 ? requested : 1;
  const [query, setQuery] = useState(search);
  const [composing, setComposing] = useState(false);
  const [data, setData] = useState<Page<DirectoryPlace> | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [current, setCurrent] = useState<DirectoryPlace | null>(null);
  const [error, setError] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadedKey, setLoadedKey] = useState("");
  const [attempt, setAttempt] = useState(0);
  const requestKey = JSON.stringify([
    branch,
    parent,
    search,
    kind,
    page,
    attempt,
  ]);
  const input = useRef<HTMLInputElement>(null);
  const results = useRef<HTMLDivElement>(null);
  const browsing = !search && !parent && !kind;
  const typing = query.trim() !== search;
  const busy = loading || typing || composing || loadedKey !== requestKey;
  useEffect(() => setQuery(search), [search]);
  useEffect(() => {
    if (!typing || composing) return;
    const timer = setTimeout(() => {
      setParams(
        {
          branch,
          ...(query.trim() ? { search: query.trim() } : {}),
          ...(kind ? { kind } : {}),
        },
        { replace: true },
      );
    }, 300);
    return () => clearTimeout(timer);
  }, [query, branch, kind, typing, composing, setParams]);
  useEffect(() => {
    const controller = new AbortController();
    setSummary(null);
    api<Summary>("/api/directory/summary", { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setSummary(result);
      })
      .catch(() => {}); // The required list request below owns visible error/retry.
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setData(null);
    setCurrent(null);
    setError(0);
    const queryParams = new URLSearchParams({
      branch: browsing ? (branch === "census2022" ? branch : "portal") : branch,
      page: String(page),
      page_size: "12",
    });
    if (search) queryParams.set("search", search);
    if (parent) queryParams.set("parent_id", parent);
    if (kind) queryParams.set("kind", kind);
    else if (browsing) queryParams.set("kind", "district");
    Promise.all([
      api<Page<DirectoryPlace>>(`/api/directory?${queryParams}`, {
        signal: controller.signal,
      }),
      parent
        ? api<DirectoryPlace>(`/api/directory/${parent}`, {
            signal: controller.signal,
          })
        : Promise.resolve(null),
    ])
      .then(([result, node]) => {
        if (!controller.signal.aborted) {
          setData(result);
          setCurrent(node);
        }
      })
      .catch((failure) => {
        if (!controller.signal.aborted)
          setError(failure instanceof ApiError ? failure.status : 503);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
          setLoadedKey(requestKey);
        }
      });
    return () => controller.abort();
  }, [branch, parent, search, kind, page, attempt, browsing, requestKey]);
  function searchFor(value: string) {
    setQuery(value);
    setParams({
      branch: "all",
      ...(value.trim() ? { search: value.trim() } : {}),
    });
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    setParams({
      branch,
      ...(query.trim() ? { search: query.trim() } : {}),
      ...(kind ? { kind } : {}),
    });
  }
  function browse(id: string, source: string) {
    setQuery("");
    setParams({ branch: source, parent: id });
  }
  function changePage(nextPage: number) {
    setParams((old) => {
      const next = new URLSearchParams(old);
      next.set("page", String(nextPage));
      return next;
    });
    results.current?.focus();
  }
  return (
    <div className="area-explorer">
      <section className="explorer-hero" aria-labelledby="explorer-title">
        <div className="explorer-hero-copy">
          <span className="explorer-eyebrow">
            <FiMapPin aria-hidden="true" /> সিলেট বিভাগের এলাকার খোঁজ
          </span>
          <h1 id="explorer-title">
            আপনার এলাকা খুঁজে নিন<span>খবর থাকুক হাতের কাছেই।</span>
          </h1>
          <p>
            গ্রাম, মহল্লা, ইউনিয়ন বা উপজেলার নাম লিখুন। এলাকার পরিচয় মিলিয়ে
            বিদ্যুতের তথ্য দেখুন।
          </p>
        </div>
        <div className="explorer-emblem" aria-hidden="true">
          <FiMapPin />
          <span>সিলেট</span>
        </div>
      </section>
      <section className="explorer-search-panel" aria-label="এলাকা অনুসন্ধান">
        <form className="explorer-search" role="search" onSubmit={submit}>
          <label htmlFor="directory-query">কোন এলাকা খুঁজছেন?</label>
          <div className="explorer-input-row">
            <FiSearch aria-hidden="true" />
            <input
              id="directory-query"
              ref={input}
              value={query}
              maxLength={100}
              autoComplete="off"
              placeholder="যেমন: আম্বরখানা, বালাগঞ্জ, Sylhet…"
              aria-describedby="directory-search-hint"
              aria-controls="directory-results"
              onChange={(event) => setQuery(event.target.value)}
              onCompositionStart={() => setComposing(true)}
              onCompositionEnd={() => setComposing(false)}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  searchFor("");
                  input.current?.focus();
                }
                if (event.key === "ArrowDown" && !busy) {
                  event.preventDefault();
                  results.current
                    ?.querySelector<HTMLElement>("button, a, summary")
                    ?.focus();
                }
              }}
            />
            {query && (
              <button
                type="button"
                className="explorer-clear"
                aria-label="অনুসন্ধান মুছুন"
                onClick={() => {
                  searchFor("");
                  input.current?.focus();
                }}
              >
                <FiX aria-hidden="true" />
              </button>
            )}
            <button
              className="btn btn-primary"
              type="submit"
              aria-label="খুঁজুন"
            >
              <FiSearch aria-hidden="true" />
              <span>খুঁজুন</span>
            </button>
          </div>
          <p id="directory-search-hint">
            বাংলা বা ইংরেজিতে লিখুন—টাইপ করলেই ফল দেখাবে। একই নাম হলে জেলা ও
            উপজেলার পরিচয় মিলিয়ে নিন।
          </p>
        </form>
        <div className="explorer-quick">
          <span>খুঁজে দেখুন</span>
          {["আম্বরখানা", "বালাগঞ্জ", "সিলেট সিটি", "মৌলভীবাজার"].map((term) => (
            <button key={term} type="button" onClick={() => searchFor(term)}>
              {term}
              <FiArrowRight aria-hidden="true" />
            </button>
          ))}
        </div>
      </section>
      <div className="explorer-content">
        <section className="explorer-main">
          <div className="explorer-filters">
            <div
              className="explorer-tabs"
              role="group"
              aria-label="তালিকার ধরন"
            >
              {[
                ["all", "সব এলাকা"],
                ["portal", "বর্তমান প্রশাসনিক"],
                ["census2022", "গ্রাম ও মহল্লা · ২০২২"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  aria-pressed={branch === value}
                  onClick={() => {
                    setParams({
                      branch: value,
                      ...(query.trim() ? { search: query.trim() } : {}),
                    });
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <label className="explorer-kind">
              ধরন
              <select
                aria-label="ধরন"
                value={kind}
                onChange={(event) =>
                  setParams({
                    branch,
                    ...(search ? { search } : {}),
                    ...(parent ? { parent } : {}),
                    ...(event.target.value ? { kind: event.target.value } : {}),
                  })
                }
              >
                <option value="">সব ধরন</option>
                {Object.entries(labels)
                  .filter(
                    ([value]) =>
                      branch !== "portal" ||
                      [
                        "division",
                        "district",
                        "upazila",
                        "city_corporation",
                        "union",
                        "ward",
                      ].includes(value),
                  )
                  .filter(
                    ([value]) =>
                      branch !== "census2022" ||
                      !["division", "ward"].includes(value),
                  )
                  .map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
              </select>
            </label>
          </div>
          {current && (
            <nav className="explorer-breadcrumb" aria-label="তালিকার পূর্বসূরি">
              <button onClick={() => searchFor("")}>সব জেলা</button>
              {current.ancestors.map((node) => (
                <span key={node.id}>
                  <FiChevronRight aria-hidden="true" />
                  <button onClick={() => browse(node.id, current.branch)}>
                    {node.name}
                  </button>
                </span>
              ))}
              <span>
                <FiChevronRight aria-hidden="true" />
                {name(current)}
              </span>
            </nav>
          )}
          {branch === "census2022" && (
            <p className="explorer-note directory-warning">
              <FiInfo aria-hidden="true" />
              <span>
                ২০২২ সালের এলাকার পরিচয়। বর্তমান রিপোর্টের এলাকা নয়; সীমানা ও
                প্রতিটি মূল পৃষ্ঠার মিল যাচাই বাকি।
              </span>
            </p>
          )}
          <div
            id="directory-results"
            ref={results}
            tabIndex={-1}
            aria-busy={busy}
          >
            <div className="explorer-results-heading">
              <h2>
                {current
                  ? `${name(current)}-এর অন্তর্গত এলাকা`
                  : browsing
                    ? "জেলা থেকে শুরু করুন"
                    : search
                      ? `“${search}” এর ফলাফল`
                      : "এলাকার তালিকা"}
              </h2>
              <span role="status">
                {busy
                  ? "খোঁজা হচ্ছে…"
                  : error
                    ? ""
                    : data
                      ? `${number(data.total)}টি ফল`
                      : ""}
              </span>
            </div>
            {busy ? (
              <div className="explorer-skeletons" aria-label="এলাকা লোড হচ্ছে">
                {[0, 1, 2, 3].map((key) => (
                  <div key={key}>
                    <span />
                    <span />
                    <span />
                  </div>
                ))}
              </div>
            ) : error ? (
              <div className="explorer-error" role="alert">
                <FiRefreshCw aria-hidden="true" />
                <h3>এলাকার তালিকায় সংযোগ হচ্ছে না</h3>
                <p>
                  {[404, 422].includes(error)
                    ? "ওয়েবসাইট ও এলাকার সেবা একই সংস্করণে চলছে না। সেবা হালনাগাদ হলে এখানে আবার চেষ্টা করুন।"
                    : "এই মুহূর্তে এলাকার তথ্য আনা যায়নি। একটু পরে আবার চেষ্টা করুন; আপনার লেখা নাম রাখা আছে।"}
                </p>
                <button
                  className="btn btn-primary"
                  onClick={() => setAttempt((old) => old + 1)}
                >
                  আবার চেষ্টা করুন
                </button>
                <Link to="/help">সহায়তা দেখুন</Link>
                {[404, 422].includes(error) && (
                  <details>
                    <summary>নিজের কম্পিউটারে চালাচ্ছেন?</summary>
                    <p>
                      পুরোনো frontend ও backend terminal-এ Ctrl+C দিন। সর্বশেষ
                      কোড নেওয়ার পরে project folder-এর START-WEBSITE.cmd চালান।
                      এটি দুই সেবা ও এলাকার search একসঙ্গে পরীক্ষা করে।
                    </p>
                  </details>
                )}
              </div>
            ) : data?.items.length ? (
              <ul className="directory-results explorer-cards">
                {data.items.map((place) => (
                  <li className="explorer-card" key={place.id}>
                    <div className="explorer-card-top">
                      <span className="explorer-place-icon">
                        <FiMapPin aria-hidden="true" />
                      </span>
                      <span
                        className={`explorer-status ${place.branch === "census2022" ? "historical" : place.reportable ? "checked" : "pending"}`}
                      >
                        {place.branch === "census2022" ? (
                          "২০২২ সালের তালিকা"
                        ) : place.reportable ? (
                          <>
                            <FiCheckCircle aria-hidden="true" /> প্রশাসনিক
                            পরিচয় যাচাইকৃত
                          </>
                        ) : (
                          "পরিচয় যাচাই বাকি"
                        )}
                      </span>
                    </div>
                    <h3>{name(place)}</h3>
                    <span className="explorer-type">
                      {labels[place.kind] || place.kind}
                      {place.name_bn &&
                      place.name_en &&
                      place.name_bn !== place.name_en
                        ? ` · ${place.name_en}`
                        : ""}
                    </span>
                    <p className="explorer-path">
                      {place.ancestors.map((node) => node.name).join(" › ") ||
                        "সিলেট বিভাগের তালিকা"}
                    </p>
                    {place.branch === "census2022" && (
                      <p className="explorer-card-note">
                        ঐতিহাসিক এলাকার পরিচয়; বর্তমান বিদ্যুৎ রিপোর্টের সঙ্গে
                        যুক্ত নয়।
                      </p>
                    )}
                    <div className="explorer-card-actions">
                      {place.children_count > 0 && (
                        <button
                          className="btn btn-sm btn-outline"
                          onClick={() => browse(place.id, place.branch)}
                        >
                          উপ-এলাকা ({number(place.children_count)})
                          <FiArrowRight aria-hidden="true" />
                        </button>
                      )}
                      {place.reportable && place.location_id && (
                        <Link
                          className="explorer-power-link"
                          to={`/?location_id=${place.location_id}`}
                        >
                          বিদ্যুৎ তথ্য দেখুন
                          <FiArrowRight aria-hidden="true" />
                        </Link>
                      )}
                    </div>
                    <details className="explorer-source">
                      <summary>পরিচয় ও মূল উৎস</summary>
                      <p>
                        {place.branch === "census2022"
                          ? `জনশুমারি ২০২২ · প্রদত্ত PDF পৃষ্ঠা ${place.pdf_page_claimed}। প্রতিটি পৃষ্ঠার সঙ্গে মিল পুনরায় যাচাই করা হয়নি।`
                          : place.reportable
                            ? "এই নাম সরকারি উৎসের সঙ্গে মিলেছে। প্রশাসনিক পরিচয় থেকে বিদ্যুৎ সরবরাহের সীমানা নির্ধারণ করা হয় না।"
                            : "মূল তালিকায় এই নাম আছে; বর্তমান প্রশাসনিক পরিচয় যাচাই বাকি থাকায় রিপোর্ট দেওয়া যাবে না।"}
                      </p>
                      <a
                        href={place.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {place.branch === "census2022"
                          ? "জনশুমারির মূল PDF"
                          : "সরকারি উৎস খুলুন"}
                        <FiExternalLink aria-hidden="true" />
                      </a>
                    </details>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="explorer-empty">
                <FiSearch aria-hidden="true" />
                <h3>
                  {summary?.available === false
                    ? "এলাকার তালিকা এখনো যুক্ত হয়নি"
                    : "এই অনুসন্ধানে এলাকা পাওয়া যায়নি"}
                </h3>
                <p>
                  {summary?.available === false
                    ? "সেবার এলাকার তথ্য প্রস্তুত করা প্রয়োজন। নিজের কম্পিউটারে সর্বশেষ START-WEBSITE.cmd চালালে তালিকা যুক্ত হবে।"
                    : "নামের ছোট অংশ লিখুন বা বাংলা ও ইংরেজি বানান বদলে দেখুন। সব গ্রামের বাংলা নাম এবং সব জেলার গ্রামের তথ্য এখনো নেই।"}
                </p>
                <button
                  className="btn btn-outline"
                  onClick={() => searchFor("")}
                >
                  সব জেলার তালিকা দেখুন
                </button>
              </div>
            )}
            {!busy && !error && data && data.total > 12 && (
              <nav className="explorer-pager" aria-label="ফলাফলের পৃষ্ঠা">
                <button
                  className="btn btn-outline btn-sm"
                  disabled={page <= 1}
                  onClick={() => changePage(page - 1)}
                >
                  <FiArrowLeft aria-hidden="true" />
                  আগের পৃষ্ঠা
                </button>
                <span>
                  {number(page)} / {number(Math.ceil(data.total / 12))}
                </span>
                <button
                  className="btn btn-outline btn-sm"
                  disabled={page * 12 >= data.total}
                  onClick={() => changePage(page + 1)}
                >
                  পরের পৃষ্ঠা
                  <FiArrowRight aria-hidden="true" />
                </button>
              </nav>
            )}
          </div>
        </section>
        <aside className="explorer-guide" aria-label="এলাকা খোঁজার সহায়তা">
          <span className="explorer-guide-icon">
            <FiLayers aria-hidden="true" />
          </span>
          <h2>ঠিক এলাকাটি চিনবেন কীভাবে?</h2>
          <ol>
            <li>
              <strong>নাম লিখুন</strong>
              <p>পুরো নাম না জানলে নামের অংশ দিয়েও খুঁজতে পারেন।</p>
            </li>
            <li>
              <strong>পরিচয় মিলিয়ে নিন</strong>
              <p>একই নামের এলাকা থাকতে পারে। জেলা, উপজেলা ও ইউনিয়ন দেখুন।</p>
            </li>
            <li>
              <strong>তথ্য দেখুন</strong>
              <p>
                যাচাইকৃত প্রশাসনিক এলাকার বিদ্যুৎ তথ্য খুলুন। নিজের সংযোগের
                রিপোর্ট দিতে প্রবেশ করুন।
              </p>
            </li>
          </ol>
          <div className="explorer-coverage">
            <FiInfo aria-hidden="true" />
            <p>
              গ্রাম ও মহল্লার ঐতিহাসিক তালিকা সিলেট জেলার। হবিগঞ্জ, মৌলভীবাজার ও
              সুনামগঞ্জের গ্রামের পূর্ণ তালিকা এখনো নেই।
            </p>
          </div>
          <Link to="/help">
            ব্যবহার নির্দেশনা
            <FiArrowRight aria-hidden="true" />
          </Link>
        </aside>
      </div>
      {summary?.available && (
        <details className="explorer-provenance">
          <summary>
            <FiCheckCircle aria-hidden="true" /> তথ্যের উৎস ও যাচাইয়ের সীমা{" "}
            <span>{number(summary.sources.length)}টি উৎস</span>
          </summary>
          <p>
            {number(summary.counts.portal || 0)}টি প্রশাসনিক রেকর্ড এবং আলাদা
            ২০২২ সালের {number(summary.counts.census2022 || 0)}টি ঐতিহাসিক
            রেকর্ড। এগুলো যোগ করে স্বতন্ত্র এলাকার মোট সংখ্যা ধরা যাবে না।
            ২০২২-এর তালিকায় কিছু বাংলা বানান শুধু খোঁজার সুবিধার জন্য যুক্ত।
            নাম পাওয়া মানেই বিদ্যুতের বর্তমান অবস্থা জানা নয়।
          </p>
          <ul>
            {summary.sources.map((source) => (
              <li key={source.id}>
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.title}
                  <FiExternalLink aria-hidden="true" />
                </a>
                <small>{source.scope}</small>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
