import { useEffect, useState, useRef } from "react";
import { api, type Location, type Page } from "../client";
export function LocationPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (id: string) => void;
}) {
  const [chain, setChain] = useState<Location[]>([]),
    [children, setChildren] = useState<Location[]>([]),
    [query, setQuery] = useState(""),
    [results, setResults] = useState<Location[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [searchLoading, setSearchLoading] = useState(false);
  const [page, setPage] = useState(1),
    [total, setTotal] = useState(0);
  const choice = useRef(0);
  const parent = chain.at(-1)?.id;
  useEffect(() => {
    setPage(1);
    choice.current++;
  }, [parent]);
  useEffect(() => {
    const c = new AbortController();
    setLoading(true);
    setError("");
    api<Page<Location>>(
      parent
        ? `/api/locations/${parent}/children?page_size=100&page=${page}`
        : `/api/locations?roots_only=true&page_size=100&page=${page}`,
      { signal: c.signal },
    )
      .then((r) => {
        if (!c.signal.aborted) {
          setChildren(r.items);
          setTotal(r.total);
        }
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, [parent, page]);
  useEffect(() => {
    const c = new AbortController();
    if (!query.trim()) {
      setResults([]);
      setSearchLoading(false);
      return () => c.abort();
    }
    setSearchLoading(true);
    const timer = setTimeout(
      () =>
        api<Page<Location>>(
          `/api/locations?search=${encodeURIComponent(query)}&page_size=20`,
          { signal: c.signal },
        )
          .then((r) => {
            if (!c.signal.aborted) setResults(r.items);
          })
          .catch((e) => {
            if (!c.signal.aborted) setError(e.message);
          })
          .finally(() => {
            if (!c.signal.aborted) setSearchLoading(false);
          }),
      250,
    );
    return () => {
      clearTimeout(timer);
      c.abort();
    };
  }, [query]);
  useEffect(() => {
    if (!value) return;
    const c = new AbortController();
    Promise.all([
      api<Location>(`/api/locations/${value}`, { signal: c.signal }),
      api<{ items: Location[] }>(`/api/locations/${value}/ancestors`, {
        signal: c.signal,
      }),
    ])
      .then(([node, ancestors]) => {
        if (!c.signal.aborted) setChain([...ancestors.items, node]);
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [value]);
  function choose(node: Location) {
    setChain([...chain, node]);
    onChange(node.verification_status === "verified" ? node.id : "");
    setQuery("");
  }
  return (
    <div className="form-stack">
      <label className="field">
        এলাকার নাম বা ID খুঁজুন
        <input
          className="input input-bordered"
          value={query}
          onChange={(e) => {
            choice.current++;
            setResults([]);
            setQuery(e.target.value);
          }}
          placeholder="বাংলা / English / alias"
        />
      </label>
      {query && (
        <p role="status">
          {searchLoading
            ? "খোঁজা হচ্ছে…"
            : !results.length
              ? "কোনো এলাকা পাওয়া যায়নি।"
              : ""}
        </p>
      )}
      {query && (
        <ul>
          {results.map((node) => (
            <li key={node.id}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={async () => {
                  const ticket = ++choice.current;
                  try {
                    const a = await api<{ items: Location[] }>(
                      `/api/locations/${node.id}/ancestors`,
                    );
                    if (ticket !== choice.current) return;
                    setChain([...a.items, node]);
                    onChange(
                      node.verification_status === "verified" ? node.id : "",
                    );
                    setQuery("");
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                {node.ancestor_names?.join(" / ")} / {node.name_bn} ·{" "}
                {node.name_en} · {node.kind}
              </button>
            </li>
          ))}
        </ul>
      )}
      <nav aria-label="এলাকার পূর্বসূরি" className="inline-actions">
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => {
            setChain([]);
            onChange("");
          }}
        >
          শুরু
        </button>
        {chain.map((node, index) => (
          <button
            key={node.id}
            type="button"
            className="btn btn-sm"
            onClick={() => {
              setChain(chain.slice(0, index + 1));
              onChange(node.verification_status === "verified" ? node.id : "");
            }}
          >
            {node.name_bn}
          </button>
        ))}
      </nav>
      <label className="field">
        {parent ? "পরের প্রশাসনিক স্তর" : "বিভাগ"}
        <select
          aria-label={parent ? "পরের প্রশাসনিক স্তর" : "বিভাগ"}
          className="select select-bordered"
          value=""
          disabled={loading}
          onChange={(e) => {
            const node = children.find((n) => n.id === e.target.value);
            if (node) choose(node);
          }}
        >
          <option value="">
            {loading
              ? "লোড হচ্ছে…"
              : children.length
                ? "এলাকা বাছুন"
                : "আর কোনো উপ-এলাকা নেই"}
          </option>
          {children.map((node) => (
            <option key={node.id} value={node.id}>
              {node.name_bn} · {node.kind}
            </option>
          ))}
        </select>
      </label>
      {chain.length > 0 && !value && (
        <p className="hint">
          এই এলাকা যাচাইকৃত নয়; রিপোর্টের জন্য যাচাইকৃত এলাকা বাছুন।
        </p>
      )}
      <div className="inline-actions">
        <button
          type="button"
          className="btn btn-sm"
          disabled={page <= 1 || loading}
          onClick={() => setPage(page - 1)}
        >
          পূর্ববর্তী
        </button>
        <button
          type="button"
          className="btn btn-sm"
          disabled={page * 100 >= total || loading}
          onClick={() => setPage(page + 1)}
        >
          পরবর্তী
        </button>
      </div>
      {error && (
        <p role="alert" className="alert alert-error">
          {error}
        </p>
      )}
    </div>
  );
}
