import { useEffect, useId, useRef, useState } from "react";
import { FiArrowRight, FiCheck, FiMapPin, FiSearch, FiX } from "react-icons/fi";
import { api, shortTime, type Location, type Page } from "../client";

export function LocationPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (id: string) => void;
}) {
  const hint = useId();
  const input = useRef<HTMLInputElement>(null);
  const resultList = useRef<HTMLUListElement>(null);
  const ticket = useRef(0);
  const choiceRequest = useRef<AbortController | null>(null);
  const emitted = useRef<string | null>(null);
  const [chain, setChain] = useState<Location[]>([]);
  const [children, setChildren] = useState<Location[]>([]);
  const [featured, setFeatured] = useState<Location[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Location[]>([]);
  const [browseError, setBrowseError] = useState("");
  const [searchError, setSearchError] = useState("");
  const [choiceError, setChoiceError] = useState("");
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [choosing, setChoosing] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState({ parent: "", page: 1 });
  const parent = chain.at(-1)?.id || "";
  const page = pages.parent === parent ? pages.page : 1;
  const term = query.normalize("NFKC").trim();
  const selected = chain.at(-1);
  const wardList =
    children.length > 0 && children.every((node) => node.kind === "ward");

  useEffect(() => {
    const controller = new AbortController();
    api<Page<Location>>(
      "/api/locations?kind=city_corporation&status=verified&page_size=4",
      { signal: controller.signal },
    )
      .then((data) => {
        if (!controller.signal.aborted) setFeatured(data.items);
      })
      .catch(() => {}); // Optional shortcuts; the actual browse request has an explicit error/retry.
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setBrowseError("");
    api<Page<Location>>(
      parent
        ? `/api/locations/${parent}/children?page_size=100&page=${page}`
        : `/api/locations?roots_only=true&page_size=100&page=${page}`,
      { signal: controller.signal },
    )
      .then((data) => {
        if (!controller.signal.aborted) {
          setChildren(data.items);
          setTotal(data.total);
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) setBrowseError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [parent, page, attempt]);
  useEffect(() => {
    const controller = new AbortController();
    setSearchError("");
    setResults([]);
    if (!term) {
      setSearchLoading(false);
      return () => controller.abort();
    }
    setSearchLoading(true);
    const timer = setTimeout(() => {
      api<Page<Location>>(
        `/api/locations?search=${encodeURIComponent(term)}&page_size=20`,
        { signal: controller.signal },
      )
        .then((data) => {
          if (!controller.signal.aborted) setResults(data.items);
        })
        .catch((error) => {
          if (!controller.signal.aborted) setSearchError(error.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setSearchLoading(false);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [term, attempt]);
  useEffect(() => {
    if (!value) {
      // Preserve deliberate browsing through an unverified parent, while an
      // external reset of a previously selected area really clears its children.
      if (emitted.current !== "") setChain([]);
      return;
    }
    const controller = new AbortController();
    setChoiceError("");
    Promise.all([
      api<Location>(`/api/locations/${value}`, { signal: controller.signal }),
      api<{ items: Location[] }>(`/api/locations/${value}/ancestors`, {
        signal: controller.signal,
      }),
    ])
      .then(([node, ancestors]) => {
        if (!controller.signal.aborted) setChain([...ancestors.items, node]);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setChoiceError(error.message);
      });
    return () => controller.abort();
  }, [value, attempt]);
  useEffect(
    () => () => {
      ticket.current++;
      choiceRequest.current?.abort();
    },
    [],
  );

  function emit(node: Location | null, nextChain: Location[]) {
    ticket.current++;
    choiceRequest.current?.abort();
    setChoosing(false);
    setChoiceError("");
    setChain(nextChain);
    const id = node?.verification_status === "verified" ? node.id : "";
    emitted.current = id;
    onChange(id);
    setQuery("");
  }
  async function resolve(node: Location) {
    choiceRequest.current?.abort();
    const controller = new AbortController();
    choiceRequest.current = controller;
    const current = ++ticket.current;
    setChoosing(true);
    setChoiceError("");
    try {
      const ancestors = await api<{ items: Location[] }>(
        `/api/locations/${node.id}/ancestors`,
        { signal: controller.signal },
      );
      if (current === ticket.current && !controller.signal.aborted)
        emit(node, [...ancestors.items, node]);
    } catch (error) {
      if (current === ticket.current && !controller.signal.aborted)
        setChoiceError((error as Error).message);
    } finally {
      if (current === ticket.current) setChoosing(false);
    }
  }
  function editQuery(next: string) {
    ticket.current++;
    choiceRequest.current?.abort();
    setChoosing(false);
    setChoiceError("");
    setResults([]);
    setQuery(next);
  }
  const error = term ? searchError || choiceError : browseError || choiceError;
  return (
    <div className="location-finder">
      <label className="field location-search-label">
        এলাকার নাম খুঁজুন
        <span className="location-search-input">
          <FiSearch aria-hidden="true" />
          <input
            ref={input}
            className="input input-bordered"
            value={query}
            onChange={(event) => editQuery(event.target.value)}
            placeholder="সিলেট, Ward 1 অথবা ওয়ার্ড ১"
            aria-describedby={hint}
            maxLength={100}
            autoComplete="off"
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                resultList.current
                  ?.querySelector<HTMLButtonElement>("button")
                  ?.focus();
              }
              if (event.key === "Escape") editQuery("");
            }}
          />
          {query && (
            <button
              type="button"
              className="btn btn-ghost"
              aria-label="অনুসন্ধান মুছুন"
              tabIndex={-1}
              onClick={() => {
                editQuery("");
                input.current?.focus();
              }}
            >
              <FiX aria-hidden="true" />
            </button>
          )}
        </span>
      </label>
      <p id={hint} className="hint finder-hint">
        বাংলা বা ইংরেজি নাম লিখুন। ফলাফলে সিটি ও ওয়ার্ডের পরিচয় মিলিয়ে নিন।
      </p>
      {term && (
        <>
          <p className="search-feedback" role="status">
            {searchLoading
              ? "এলাকা খোঁজা হচ্ছে…"
              : error
                ? "অনুসন্ধান সম্পন্ন হয়নি। আবার চেষ্টা করুন।"
                : results.length
                  ? `${results.length.toLocaleString("bn-BD")}টি ফলাফল · বেছে নিতে ক্লিক বা Tab ব্যবহার করুন`
                  : "এই নামে কোনো এলাকা পাওয়া যায়নি। নিচে সিটি বেছে ওয়ার্ডের তালিকা দেখতে পারেন।"}
          </p>
          {results.length > 0 && (
            <ul
              className="location-search-results"
              ref={resultList}
              onKeyDown={(event) => {
                const buttons = [
                  ...event.currentTarget.querySelectorAll<HTMLButtonElement>(
                    "button",
                  ),
                ];
                const index = buttons.indexOf(
                  document.activeElement as HTMLButtonElement,
                );
                if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                  event.preventDefault();
                  buttons[
                    (index +
                      (event.key === "ArrowDown" ? 1 : -1) +
                      buttons.length) %
                      buttons.length
                  ]?.focus();
                }
                if (event.key === "Escape") {
                  editQuery("");
                  input.current?.focus();
                }
              }}
            >
              {results.map((node) => (
                <li key={node.id}>
                  <button
                    type="button"
                    className="location-result"
                    disabled={choosing}
                    onClick={() => void resolve(node)}
                  >
                    <FiMapPin aria-hidden="true" />
                    <span>
                      <span className="result-path">
                        {node.ancestor_names?.length
                          ? node.ancestor_names.join(" / ") + " / "
                          : ""}
                        {node.name_bn}
                      </span>
                      <small>
                        {node.name_en} · {locationKind(node.kind)}
                        {node.verification_status !== "verified"
                          ? " · যাচাই বাকি"
                          : ""}
                      </small>
                    </span>
                    <FiArrowRight aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {error && (
        <div className="alert alert-error" role="alert">
          <span>{error}</span>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => {
              setAttempt((old) => old + 1);
            }}
          >
            এলাকা আবার লোড করুন
          </button>
        </div>
      )}
      {choosing && <p role="status">এলাকার পরিচয় মিলিয়ে নেওয়া হচ্ছে…</p>}
      {!parent && featured.length > 0 && (
        <div className="featured-places">
          <span>সরাসরি বাছুন</span>
          {featured.map((node) => (
            <button
              key={node.id}
              type="button"
              className="btn btn-outline"
              disabled={choosing}
              onClick={() => void resolve(node)}
            >
              <FiMapPin aria-hidden="true" />
              {node.name_bn}
              <FiArrowRight aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
      {chain.length > 0 && (
        <nav
          aria-label="এলাকার পূর্বসূরি"
          className="inline-actions location-breadcrumb"
        >
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => emit(null, [])}
          >
            শুরু
          </button>
          {chain.map((node, index) => (
            <button
              key={node.id}
              type="button"
              className="btn btn-sm"
              aria-current={node.id === parent ? "location" : undefined}
              onClick={() => emit(node, chain.slice(0, index + 1))}
            >
              {node.name_bn}
            </button>
          ))}
        </nav>
      )}
      {loading && (
        <p role="status" className="finder-loading">
          এলাকার তালিকা লোড হচ্ছে…
        </p>
      )}
      {!wardList && (loading || children.length > 0) && (
        <label className="field">
          {parent ? "পরের প্রশাসনিক স্তর" : "বিভাগ"}
          <select
            aria-label={parent ? "পরের প্রশাসনিক স্তর" : "বিভাগ"}
            className="select select-bordered"
            value=""
            disabled={loading}
            onChange={(event) => {
              const node = children.find(
                (row) => row.id === event.target.value,
              );
              if (node) emit(node, [...chain, node]);
            }}
          >
            <option value="">{loading ? "লোড হচ্ছে…" : "এলাকা বাছুন"}</option>
            {children.map((node) => (
              <option key={node.id} value={node.id}>
                {node.name_bn} · {locationKind(node.kind)}
              </option>
            ))}
          </select>
        </label>
      )}
      {!loading && wardList && (
        <section className="ward-options" aria-label="ওয়ার্ড বাছুন">
          <h3>
            আপনার ওয়ার্ড বেছে নিন{" "}
            <span>{total.toLocaleString("bn-BD")}টি ওয়ার্ড</span>
          </h3>
          <div className="ward-grid">
            {children.map((node) => (
              <button
                type="button"
                className="btn btn-outline"
                key={node.id}
                onClick={() => emit(node, [...chain, node])}
              >
                {node.name_bn}
              </button>
            ))}
          </div>
          <p className="hint">
            ওয়ার্ডের প্রশাসনিক পরিচয় দেখানো হচ্ছে। এখান থেকে বিদ্যুতের ফিডার
            বা সরবরাহের অবস্থা অনুমান করা হয় না।
          </p>
        </section>
      )}
      {selected && value && (
        <div className="chosen-location">
          <FiCheck aria-hidden="true" />
          <div>
            <strong>নির্বাচিত: {selected.name_bn}</strong>
            {selected.source_url && (
              <small>
                প্রশাসনিক পরিচয়:{" "}
                <a
                  href={selected.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  মূল উৎস ↗
                </a>
                {selected.verified_at
                  ? ` · যাচাই ${shortTime(selected.verified_at)}`
                  : ""}
              </small>
            )}
          </div>
        </div>
      )}
      {chain.length > 0 && !value && (
        <p className="hint">
          এই ধাপটি যাচাইকৃত নয়। নিচের যাচাইকৃত এলাকা বেছে রিপোর্ট দিন।
        </p>
      )}
      {!loading && !term && !children.length && !browseError && !parent && (
        <p className="location-empty" role="status">
          এখনো কোনো এলাকা প্রকাশিত হয়নি। যাচাই করে এলাকা যোগ হলে এখানে খুঁজে
          পাবেন।
        </p>
      )}
      {total > 100 && (
        <div className="inline-actions">
          <button
            type="button"
            className="btn btn-sm"
            disabled={page <= 1 || loading}
            onClick={() => setPages({ parent, page: page - 1 })}
          >
            পূর্ববর্তী
          </button>
          <button
            type="button"
            className="btn btn-sm"
            disabled={page * 100 >= total || loading}
            onClick={() => setPages({ parent, page: page + 1 })}
          >
            পরবর্তী
          </button>
        </div>
      )}
    </div>
  );
}
function locationKind(kind: string) {
  return (
    (
      {
        division: "বিভাগ",
        district: "জেলা",
        city_corporation: "সিটি কর্পোরেশন",
        upazila: "উপজেলা",
        ward: "ওয়ার্ড",
        union: "ইউনিয়ন",
        village: "গ্রাম",
        neighborhood: "পাড়া / মহল্লা",
      } as Record<string, string>
    )[kind] || kind
  );
}
