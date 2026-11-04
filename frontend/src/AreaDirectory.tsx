import { useEffect, useState, type FormEvent } from "react";
import { FiArrowRight, FiMapPin, FiSearch } from "react-icons/fi";
import { api, type Page } from "./client";
import { Link, useSearchParams } from "./navigation";
import { Card, EmptyState } from "./components/ui";

type Place = {
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
  warning: string;
};
type Summary = {
  available: boolean;
  counts: Record<string, number>;
  sources: { id: string; url: string; title: string; scope: string }[];
  review_queue: { name_bn: string; reason: string }[];
  electricity_references: {
    office: string;
    area_name_bn: string;
    relationship: string;
    source_id: string;
  }[];
};
const labels: Record<string, string> = {
  division: "বিভাগ",
  district: "জেলা",
  upazila: "উপজেলা",
  city_corporation: "সিটি কর্পোরেশন",
  union: "ইউনিয়ন",
  ward: "ওয়ার্ড",
  census_thana: "জনশুমারির থানা",
  ward_segment: "জনশুমারির ওয়ার্ড segment",
  mauza_segment: "মৌজা / মহল্লা segment",
  mahalla: "মহল্লা",
  village: "গ্রাম",
  municipality: "পৌরসভা",
  cantonment: "ক্যান্টনমেন্ট",
};
export function AreaDirectory() {
  const [params, setParams] = useSearchParams();
  const branch =
    params.get("branch") === "census2022" ? "census2022" : "portal";
  const parent = params.get("parent") || "";
  const search = params.get("search") || "";
  const requested = Number(params.get("page") || 1);
  const page =
    Number.isSafeInteger(requested) && requested >= 1 ? requested : 1;
  const [query, setQuery] = useState(search);
  const [data, setData] = useState<Page<Place> | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [current, setCurrent] = useState<Place | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => setQuery(search), [search]);
  useEffect(() => {
    const controller = new AbortController();
    api<Summary>("/api/directory/summary", { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setSummary(result);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setData(null);
    setCurrent(null);
    setError("");
    const queryParams = new URLSearchParams({
      branch,
      page: String(page),
      page_size: "20",
    });
    if (search) queryParams.set("search", search);
    else if (parent) queryParams.set("parent_id", parent);
    else queryParams.set("roots_only", "true");
    Promise.all([
      api<Page<Place>>(`/api/directory?${queryParams}`, {
        signal: controller.signal,
      }),
      parent
        ? api<Place>(`/api/directory/${parent}`, { signal: controller.signal })
        : Promise.resolve(null),
    ])
      .then(([result, node]) => {
        if (!controller.signal.aborted) {
          setData(result);
          setCurrent(node);
        }
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setError(failure.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [branch, parent, search, page, attempt]);
  function chooseBranch(next: string) {
    setParams({ branch: next });
  }
  function browse(id: string) {
    setParams({ branch, parent: id });
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    setParams({ branch, ...(query.trim() ? { search: query.trim() } : {}) });
  }
  return (
    <>
      <p className="eyebrow">এলাকার পরিচয় ও মূল উৎস</p>
      <h1>উপজেলা, ইউনিয়ন, গ্রাম ও মহল্লা খুঁজুন</h1>
      <p className="page-intro">
        সরকারি portal-এর তালিকা ও ২০২২ সালের দেওয়া census extraction আলাদা করে
        দেখুন। একই নামের একাধিক স্থান থাকলে পূর্বসূরি ও উৎস মিলিয়ে নিন।
      </p>
      <div className="directory-tabs" role="group" aria-label="তালিকার ধরন">
        <button
          className={
            branch === "portal" ? "btn btn-primary" : "btn btn-outline"
          }
          aria-pressed={branch === "portal"}
          onClick={() => chooseBranch("portal")}
        >
          প্রশাসনিক তালিকা{" "}
          {summary?.counts.portal
            ? `(${summary.counts.portal.toLocaleString("bn-BD")})`
            : ""}
        </button>
        <button
          className={
            branch === "census2022" ? "btn btn-primary" : "btn btn-outline"
          }
          aria-pressed={branch === "census2022"}
          onClick={() => chooseBranch("census2022")}
        >
          গ্রাম / মহল্লা · ২০২২{" "}
          {summary?.counts.census2022
            ? `(${summary.counts.census2022.toLocaleString("bn-BD")})`
            : ""}
        </button>
      </div>
      {branch === "census2022" && (
        <div className="freshness-warning directory-warning" role="note">
          <strong>ঐতিহাসিক reference—বর্তমান রিপোর্টের এলাকা নয়।</strong>
          <p>
            নামগুলো প্রদত্ত ২০২২ extraction থেকে। মূল PDF-এর প্রতিটি row/page
            পুনরায় মেলানো হয়নি। জনশুমারির থানা, ওয়ার্ড ও মৌজা segment বর্তমান
            প্রশাসনিক সীমানায় স্বয়ংক্রিয়ভাবে যুক্ত করা হয় না। অন্য তিন জেলার
            গ্রাম এই extraction-এ নেই।
          </p>
        </div>
      )}
      <Card title="এলাকা অনুসন্ধান">
        <form className="directory-search" onSubmit={submit}>
          <label className="field">
            তালিকায় নাম খুঁজুন
            <input
              className="input input-bordered"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              maxLength={100}
              placeholder={
                branch === "census2022"
                  ? "Ambarkhana, Adityapur বা আম্বরখানা"
                  : "বালাগঞ্জ, সুনামগঞ্জ, কান্দিগাঁও"
              }
            />
          </label>
          <button className="btn btn-primary" disabled={loading}>
            <FiSearch aria-hidden="true" />
            খুঁজুন
          </button>
        </form>
        <p className="hint">
          Census-এর মূল নাম English-এ। কিছু পরিচিত বাংলা search spelling সহায়ক
          হিসেবে যুক্ত; সেগুলো সীমানার প্রমাণ নয়।
        </p>
        <nav
          className="inline-actions location-breadcrumb"
          aria-label="তালিকার পূর্বসূরি"
        >
          <button className="btn btn-sm" onClick={() => setParams({ branch })}>
            তালিকার শুরু
          </button>
          {current?.ancestors.map((node) => (
            <button
              key={node.id}
              className="btn btn-sm"
              onClick={() => browse(node.id)}
            >
              {node.name}
            </button>
          ))}
          {current && <span>{current.name_bn || current.name_en}</span>}
        </nav>
      </Card>
      {error && (
        <div className="alert alert-error section-gap" role="alert">
          <span>তালিকা লোড হয়নি। {error}</span>
          <button
            className="btn btn-sm"
            onClick={() => setAttempt((old) => old + 1)}
          >
            তালিকা আবার লোড করুন
          </button>
        </div>
      )}
      {loading && (
        <p className="loading-state" role="status">
          এলাকার তালিকা লোড হচ্ছে…
        </p>
      )}
      {data && !loading && (
        <>
          <p className="directory-total" role="status">
            মোট {data.total.toLocaleString("bn-BD")}টি ফলাফল · পৃষ্ঠা{" "}
            {page.toLocaleString("bn-BD")}
            {search ? ` · “${search}”` : ""}
          </p>
          {!data.items.length && (
            <EmptyState title="এই অনুসন্ধানে কোনো এলাকা নেই">
              অন্য বানান বা নামের অংশ দিয়ে খুঁজুন। বর্তমান ও ঐতিহাসিক তালিকা
              আলাদা করে চেষ্টা করুন।
            </EmptyState>
          )}
          <ul className="directory-results">
            {data.items.map((place) => (
              <li className="panel" key={place.id}>
                <div className="directory-result-heading">
                  <FiMapPin aria-hidden="true" />
                  <h2>{place.name_bn || place.name_en}</h2>
                  <span className="badge">
                    {labels[place.kind] || place.kind}
                  </span>
                </div>
                {place.name_bn &&
                  place.name_en &&
                  place.name_bn !== place.name_en && (
                    <p className="hint">{place.name_en}</p>
                  )}
                <p className="directory-path">
                  {place.ancestors.map((node) => node.name).join(" / ") ||
                    "তালিকার মূল স্তর"}
                </p>
                <p className="fine-print">
                  {place.branch === "census2022"
                    ? `২০২২ · প্রদত্ত source code ${place.bbs_code_segments} · দেওয়া PDF page ${place.pdf_page_claimed} (মিল যাচাই বাকি)`
                    : place.reportable
                      ? "নাম মূল উৎসের সঙ্গে মিলেছে; প্রশাসনিক পরিচয় যাচাইকৃত।"
                      : "পর্যালোচনা বাকি বা বর্তমান প্রশাসনিক যাচাই স্থগিত। রিপোর্ট দেওয়া যাবে না।"}
                </p>
                <div className="inline-actions">
                  {place.children_count > 0 && (
                    <button
                      className="btn btn-outline"
                      onClick={() => browse(place.id)}
                    >
                      উপ-এলাকা ({place.children_count.toLocaleString("bn-BD")})
                      <FiArrowRight aria-hidden="true" />
                    </button>
                  )}
                  <a
                    className="btn btn-ghost"
                    href={place.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {place.branch === "census2022"
                      ? "দেওয়া PDF লিংক ↗"
                      : "মূল উৎস ↗"}
                  </a>
                  {place.reportable && place.location_id && (
                    <Link
                      className="btn btn-primary"
                      to={`/?location_id=${place.location_id}`}
                    >
                      এলাকার বিদ্যুৎ তথ্য →
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <div className="pager">
            <button
              className="btn btn-outline"
              disabled={page <= 1}
              onClick={() =>
                setParams((old) => {
                  const next = new URLSearchParams(old);
                  next.set("page", String(page - 1));
                  return next;
                })
              }
            >
              পূর্ববর্তী পৃষ্ঠা
            </button>
            <span>
              {page.toLocaleString("bn-BD")} /{" "}
              {Math.max(1, Math.ceil(data.total / 20)).toLocaleString("bn-BD")}
            </span>
            <button
              className="btn btn-outline"
              disabled={page * 20 >= data.total}
              onClick={() =>
                setParams((old) => {
                  const next = new URLSearchParams(old);
                  next.set("page", String(page + 1));
                  return next;
                })
              }
            >
              পরবর্তী পৃষ্ঠা
            </button>
          </div>
        </>
      )}
      {!!summary?.sources.length && (
        <details className="panel section-gap directory-sources">
          <summary>
            মূল source links ({summary.sources.length.toLocaleString("bn-BD")})
            ও যাচাইয়ের সীমা
          </summary>
          <p>
            লিংক থাকা মানেই প্রতিটি record বা বিদ্যুতের আওতা যাচাইকৃত নয়।
            বর্তমান ও ২০২২ সালের snapshot মিশিয়ে মোট এলাকা গণনা করবেন না।
          </p>
          <ul>
            {summary.sources.map((source) => (
              <li key={source.id}>
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.title} ↗
                </a>
                <small>{source.scope}</small>
              </li>
            ))}
          </ul>
        </details>
      )}
      {!!summary?.electricity_references.length && (
        <details className="panel section-gap directory-sources">
          <summary>বিদ্যুৎ অফিস ও স্থাননামের reference</summary>
          <p>
            এগুলো source-এ উল্লিখিত উদাহরণ। ফিডার বা বিদ্যুৎ সরবরাহের নিশ্চিত
            আওতা নয়। স্বয়ংক্রিয়ভাবে active coverage হিসেবে import করা হয়নি।
          </p>
          <ul>
            {summary.electricity_references.map((entry, index) => (
              <li key={index}>
                <strong>{entry.area_name_bn}</strong> · {entry.office}
                {summary.sources.find(
                  (source) => source.id === entry.source_id,
                ) && (
                  <a
                    href={
                      summary.sources.find(
                        (source) => source.id === entry.source_id,
                      )!.url
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {" "}
                    মূল reference ↗
                  </a>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
