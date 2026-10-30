import { SavedPager } from "./components/SavedPager";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "./navigation";
import toast from "react-hot-toast";
import { api, bdToIso, localInputTime, shortTime } from "./client";
import { Card } from "./components/ui";
import { LocationPicker } from "./components/LocationPicker";
import { TimeField, useList, useRequest } from "./management";

type Activity = {
  id: string;
  title: string;
  location_id: string;
  starts_at: string;
  ends_at: string;
  version: number;
  check: Check;
};
type Match = {
  id: string;
  version: number;
  affected_start: string;
  affected_end: string;
  affected_minutes: number;
  updated_at: string;
  coverage_confirmed: boolean;
  notice: {
    title: string;
    source_url: string;
    publisher: string;
    published_at: string | null;
    updated_at: string;
  };
};
type Check = {
  conflicts: Match[];
  uncertain: Match[];
  announced_overlap: boolean;
  affected_minutes: number;
  checked_at: string;
};
function CheckResult({ check }: { check: Check }) {
  return (
    <section className="record" aria-label="সময় মেলানোর ফল">
      <h3>
        {check.announced_overlap
          ? "আপনার কাজ ঘোষিত বিদ্যুৎ-বিরতির সময়ের সঙ্গে মিলেছে"
          : check.uncertain.length
            ? "আওতা নিশ্চিত করা যায়নি"
            : "মিলে যায় এমন প্রকাশিত বিদ্যুৎ-বিরতির ঘোষণা পাওয়া যায়নি"}
      </h3>
      <p>
        নিশ্চিত নামযুক্ত / স্পষ্ট সমগ্র এলাকার ঘোষণায় সম্মিলিত সময়:{" "}
        {check.affected_minutes.toLocaleString("bn-BD")} মিনিট। overlapping অংশ
        একবার গণনা হয়েছে।
      </p>
      <p>
        এটি পরিকল্পনার সঙ্গে তুলনা; বিদ্যুৎ থাকার নিশ্চয়তা বা বাস্তব বিভ্রাটের
        পূর্বাভাস নয়।
      </p>
      <p>এইমাত্র পরীক্ষা: {shortTime(check.checked_at)}</p>
      {[...check.conflicts, ...check.uncertain].map((x) => (
        <div className="record" key={x.id}>
          <strong>{x.notice.title}</strong>
          <span>
            {x.coverage_confirmed
              ? "ঘোষণায় আওতা মেলে"
              : "আংশিক / অনিশ্চিত আওতা · মোট সময়ে যোগ হয়নি"}
          </span>
          <span>
            কাজের প্রভাবিত অংশ: {shortTime(x.affected_start)} →{" "}
            {shortTime(x.affected_end)}
          </span>
          <a href={x.notice.source_url} target="_blank" rel="noreferrer">
            মূল ঘোষণা · {x.notice.publisher} ↗
          </a>
          <span>
            উৎস প্রকাশ: {shortTime(x.notice.published_at)} · GridWatch আপডেট:{" "}
            {shortTime(x.updated_at)} · revision {x.version}
          </span>
        </div>
      ))}
    </section>
  );
}
export function ActivitiesPage() {
  const [params, setParams] = useSearchParams();
  const area = params.get("location_id") || "";
  const [version, setVersion] = useState(0);
  const list = useList<Activity>("/api/activities", version);
  const [savedPage, setSavedPage] = useState(1);
  const saved = useRequest<{
    total: number;
    items: { id: string; name_bn: string; label: string; available: boolean }[];
  }>(
    savedPage === 1 ? "/api/saved-areas" : `/api/saved-areas?page=${savedPage}`,
  );
  const [title, setTitle] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState("");
  const [edit, setEdit] = useState<Activity | null>(null),
    [check, setCheck] = useState<Check | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    setCheck(null);
  }, [area, title, start, end]);
  const selectArea = (id: string) =>
    setParams((old) => {
      const p = new URLSearchParams(old);
      p.delete("page");
      if (id) p.set("location_id", id);
      else p.delete("location_id");
      return p;
    });
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setError("");
    setCheck(null);
    if (!area || !title.trim() || !start || !end || end <= start) {
      setError("এলাকা, কাজের নাম এবং শুরুর পরের শেষ সময় দিন।");
      return;
    }
    setBusy(true);
    try {
      const times = {
        location_id: area,
        starts_at: bdToIso(start),
        ends_at: bdToIso(end),
      };
      const item = await api<Activity>(
        edit ? `/api/activities/${edit.id}` : "/api/activities",
        {
          method: edit ? "PUT" : "POST",
          body: JSON.stringify({
            ...times,
            title,
            version: edit?.version || 1,
          }),
        },
      );
      toast.success("কাজ সংরক্ষিত");
      setEdit(item);
      setVersion((v) => v + 1);
      const fresh = await api<Activity>(`/api/activities/${item.id}`);
      setCheck(fresh.check);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function view(item: Activity) {
    if (busy) return;
    setBusy(true);
    setError("");
    setCheck(null);
    try {
      const fresh = await api<Activity>(`/api/activities/${item.id}`);
      selectArea(fresh.location_id);
      setTitle(fresh.title);
      setStart(localInputTime(new Date(fresh.starts_at)));
      setEnd(localInputTime(new Date(fresh.ends_at)));
      setEdit(fresh);
      // Display check after form-state effect clears any previous result.
      setSelected(fresh.id);
      setVersion((v) => v + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const [selected, setSelected] = useState("");
  return (
    <>
      <h1>কাজের সময় ও ঘোষণার মিল</h1>
      <div className="admin-grid">
        <Card title={edit ? "সংরক্ষিত কাজ সম্পাদনা" : "নতুন কাজ"}>
          <form className="form-stack" onSubmit={submit}>
            <fieldset disabled={busy} className="form-stack">
              <label>
                কাজের নাম
                <input
                  className="input"
                  value={title}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    setSelected("");
                  }}
                  maxLength={160}
                  required
                />
              </label>
              <label>
                সংরক্ষিত এলাকা
                <select
                  aria-label="সংরক্ষিত এলাকা"
                  className="select"
                  value={area}
                  onChange={(e) => {
                    selectArea(e.target.value);
                    setSelected("");
                  }}
                >
                  <option value="">বাছুন</option>
                  {saved.data?.items
                    .filter((x) => x.available)
                    .map((x) => (
                      <option key={x.id} value={x.id}>
                        {x.label || x.name_bn}
                      </option>
                    ))}
                </select>
              </label>
              <SavedPager
                page={savedPage}
                total={saved.data?.total ?? -1}
                loading={saved.loading}
                onChange={setSavedPage}
              />
              <LocationPicker
                value={area}
                onChange={(id) => {
                  selectArea(id);
                  setSelected("");
                }}
              />
              <TimeField
                label="শুরু"
                value={start}
                onChange={(v) => {
                  setStart(v);
                  setSelected("");
                }}
              />
              <TimeField
                label="শেষ"
                value={end}
                onChange={(v) => {
                  setEnd(v);
                  setSelected("");
                }}
              />
              <p className="hint">
                সর্বোচ্চ ৭ দিন · Asia/Dhaka · শেষে ঠিক শুরু হলে overlap নয়।
              </p>
              <button className="btn btn-primary">
                {busy ? "অপেক্ষা করুন…" : "সংরক্ষণ ও মিলিয়ে দেখুন"}
              </button>
              {edit && (
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    setEdit(null);
                    setTitle("");
                    setCheck(null);
                    setSelected("");
                  }}
                >
                  নতুন কাজ
                </button>
              )}
            </fieldset>
            {error && <p role="alert">{error}</p>}
          </form>
          {check && <CheckResult check={check} />}{" "}
          {selected && !check && (
            <FreshActivity id={selected} version={version} />
          )}
        </Card>
        <Card title="আমার সংরক্ষিত কাজ">
          <label>
            কাজ খুঁজুন
            <input
              className="input"
              value={params.get("search") || ""}
              onChange={(e) => list.update("search", e.target.value)}
            />
          </label>
          {list.loading && <p role="status">লোড হচ্ছে…</p>}
          {list.error && <p role="alert">{list.error}</p>}
          {list.data?.items.map((x) => (
            <div className="record" key={x.id}>
              <strong>{x.title}</strong>
              <span>
                {shortTime(x.starts_at)} → {shortTime(x.ends_at)}
              </span>
              <button className="btn" disabled={busy} onClick={() => view(x)}>
                খুলুন ও নতুন করে পরীক্ষা
              </button>
              <button
                className="btn btn-outline"
                disabled={busy}
                onClick={async () => {
                  if (
                    !confirm(
                      "শুধু এই সংরক্ষিত কাজটি মুছবেন? ঘোষণাগুলো অক্ষত থাকবে।",
                    )
                  )
                    return;
                  setBusy(true);
                  try {
                    await api(`/api/activities/${x.id}?version=${x.version}`, {
                      method: "DELETE",
                    });
                    toast.success("কাজ মুছে গেছে");
                    setVersion((v) => v + 1);
                    if (edit?.id === x.id) {
                      setEdit(null);
                      setCheck(null);
                      setSelected("");
                    }
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                মুছুন
              </button>
            </div>
          ))}
          {list.data?.total === 0 && <p>সংরক্ষিত কাজ নেই।</p>}
          <div className="pager">
            <button
              className="btn"
              disabled={list.page <= 1}
              onClick={() => list.update("page", String(list.page - 1))}
            >
              পূর্ববর্তী
            </button>
            <span>মোট {list.data?.total ?? "…"}</span>
            <button
              className="btn"
              disabled={!list.data || list.page * 10 >= list.data.total}
              onClick={() => list.update("page", String(list.page + 1))}
            >
              পরবর্তী
            </button>
          </div>
        </Card>
      </div>
    </>
  );
}
function FreshActivity({ id, version }: { id: string; version: number }) {
  const result = useRequest<Activity>(`/api/activities/${id}?v=${version}`);
  return (
    <>
      {result.loading && <p role="status">বর্তমান ঘোষণার সঙ্গে মিলছে…</p>}
      {result.error && <p role="alert">{result.error}</p>}
      {result.data && <CheckResult check={result.data.check} />}
    </>
  );
}
type Episode = {
  id: string;
  started_at: string | null;
  ended_at: string | null;
  is_open: boolean;
  duration_minutes: number | null;
  accepted_observations: number;
  reviewed_observations: number;
};
type History = {
  items: Episode[];
  total: number;
  summary: {
    recorded_episodes: number;
    starting_in_range: number;
    completed: number;
    open: number;
    incomplete: number;
    contradictory: number;
    overlapping_records: boolean;
    known_minutes: number;
    average_completed_minutes: number | null;
    daily: { date: string; known_minutes: number }[];
  };
};
export function HistoryPage() {
  const [params, setParams] = useSearchParams();
  const area = params.get("location_id") || "";
  const [today] = useState(() => localInputTime(new Date()).slice(0, 10));
  const [monthAgo] = useState(() =>
    localInputTime(new Date(Date.now() - 30 * 86400000)).slice(0, 10),
  );
  const start = params.get("start") || monthAgo,
    end = params.get("end") || today;
  const status = params.get("status") || "all",
    sort = params.get("sort") || "newest",
    page = Math.max(1, Number(params.get("page")) || 1);
  function update(key: string, value: string) {
    setParams((old) => {
      const p = new URLSearchParams(old);
      if (value) p.set(key, value);
      else p.delete(key);
      if (key !== "page") p.delete("page");
      return p;
    });
  }
  return (
    <>
      <h1>আমার রেকর্ড করা বিভ্রাটের ইতিহাস</h1>
      <p>
        শুধু নিজের নির্বাচিত এলাকার গৃহীত পর্যবেক্ষণ। সম্পূর্ণ monitoring নয়;
        রিপোর্টবিহীন দিন বিদ্যুৎ থাকার প্রমাণ নয়।
      </p>
      <LocationPicker value={area} onChange={(v) => update("location_id", v)} />
      <div className="toolbar">
        <label>
          শুরুর তারিখ · বাংলাদেশ
          <input
            type="date"
            className="input"
            value={start}
            onChange={(e) => update("start", e.target.value)}
          />
        </label>
        <label>
          শেষ তারিখ · অন্তর্ভুক্ত
          <input
            type="date"
            className="input"
            value={end}
            onChange={(e) => update("end", e.target.value)}
          />
        </label>
        <label>
          অবস্থা
          <select
            className="select"
            value={status}
            onChange={(e) => update("status", e.target.value)}
          >
            <option value="all">সব</option>
            <option value="completed">সম্পূর্ণ</option>
            <option value="open">খোলা</option>
            <option value="incomplete">অসম্পূর্ণ বন্ধ episode</option>
          </select>
        </label>
        <label>
          ক্রম
          <select
            className="select"
            value={sort}
            onChange={(e) => update("sort", e.target.value)}
          >
            <option value="newest">নতুন আগে</option>
            <option value="oldest">পুরোনো আগে</option>
          </select>
        </label>
      </div>
      <p className="hint">
        সক্রিয় নির্বাচন: {start} → {end} · {status}
      </p>
      {area && start && end && end >= start ? (
        <HistoryResults
          area={area}
          start={start}
          end={end}
          status={status}
          sort={sort}
          page={page}
          move={(n) => update("page", String(n))}
        />
      ) : (
        <p>এলাকা ও বৈধ তারিখ বাছুন।</p>
      )}
    </>
  );
}
function HistoryResults({
  area,
  start,
  end,
  status,
  sort,
  page,
  move,
}: {
  area: string;
  start: string;
  end: string;
  status: string;
  sort: string;
  page: number;
  move: (n: number) => void;
}) {
  const endExclusive = new Date(
    new Date(end + "T00:00:00+06:00").getTime() + 86400000,
  ).toISOString();
  const query = new URLSearchParams({
    location_id: area,
    start: start + "T00:00:00+06:00",
    end: endExclusive,
    status,
    sort,
    page: String(page),
    page_size: "10",
  });
  const result = useRequest<History>(`/api/history?${query}`);
  useEffect(() => {
    if (result.data && page > 1 && !result.data.items.length)
      move(Math.max(1, Math.ceil(result.data.total / 10)));
  }, [result.data]);
  if (result.loading) return <p role="status">ইতিহাস গণনা হচ্ছে…</p>;
  if (result.error) return <p role="alert">{result.error}</p>;
  if (!result.data) return null;
  const { summary: s, items } = result.data;
  return (
    <>
      <Card title="রেকর্ডভিত্তিক ব্যক্তিগত সারাংশ">
        <p>
          এই range-এর সঙ্গে জানা সময় মেলে এমন {s.recorded_episodes}টি episode;
          এর মধ্যে শুরু হয়েছে {s.starting_in_range}টি। অজানা শুরুতে শেষ
          পর্যবেক্ষণ থেকে range মেলানো হয়েছে।
        </p>
        <p>
          সম্পূর্ণ: {s.completed} · খোলা: {s.open} · অসম্পূর্ণ: {s.incomplete}
        </p>
        <p>
          নির্বাচিত range-এর মধ্যে জানা সম্পূর্ণ duration:{" "}
          <strong>{s.known_minutes.toLocaleString("bn-BD")} মিনিট</strong>।
          overlapping অংশ একবার; boundary-তে কাটা হয়েছে।
        </p>
        <p>
          যোগ্য সম্পূর্ণ episode-এর পুরো duration-এর গড়:{" "}
          {s.average_completed_minutes === null
            ? "নির্ণয় করা যায়নি"
            : s.average_completed_minutes.toLocaleString("bn-BD") + " মিনিট"}
          । খোলা বা অজানা সময় গড়ে নেই।
        </p>
        {(s.overlapping_records || s.contradictory > 0) && (
          <p role="alert">
            সময়ের অসঙ্গতি রয়েছে; union দিয়ে downtime গণনা, গড় দেখানো হয়নি।
            পর্যালোচনা দরকার।
          </p>
        )}
      </Card>
      <Card title="ব্যক্তিগত episodes">
        <p>
          {process.env.NEXT_PUBLIC_DEMO_INSTANCE === "true"
            ? "এটি কাল্পনিক অনুশীলনের ব্যক্তিগত ইতিহাস; বাস্তব বিভ্রাটের পরিসংখ্যান নয়। Pending ও প্রত্যাখ্যাত রিপোর্ট বাদ থাকে।"
            : "একই episode-এ একাধিক রিপোর্ট থাকতে পারে। প্রত্যাখ্যাত, pending ও demo রিপোর্ট বাদ দিয়ে ইতিহাস পুনর্গণনা হয়।"}
        </p>
        {items.map((x) => (
          <div className="record" key={x.id}>
            <strong>
              {x.is_open
                ? "খোলা · ফেরার তথ্য নেই"
                : x.duration_minutes === null
                  ? "অসম্পূর্ণ সময়"
                  : "সম্পূর্ণ"}
            </strong>
            <span>
              রিপোর্ট করা শুরু:{" "}
              {x.started_at ? shortTime(x.started_at) : "অজানা"}
            </span>
            <span>
              রিপোর্ট করা পুনরুদ্ধার:{" "}
              {x.ended_at ? shortTime(x.ended_at) : "অজানা"}
            </span>
            <span>
              Duration:{" "}
              {x.duration_minutes === null
                ? "অজানা"
                : x.duration_minutes.toLocaleString("bn-BD") + " মিনিট"}{" "}
              · গৃহীত পর্যবেক্ষণ {x.accepted_observations} · অ্যাডমিন পর্যালোচিত{" "}
              {x.reviewed_observations}
            </span>
          </div>
        ))}
        {!items.length && (
          <p>
            এই নির্বাচনে ব্যক্তিগত episode নেই। uninterrupted electricity-এর
            দাবি নয়।
          </p>
        )}
        <div className="pager">
          <button
            className="btn"
            disabled={page <= 1}
            onClick={() => move(page - 1)}
          >
            পূর্ববর্তী
          </button>
          <span>
            পৃষ্ঠা {page} · মোট {result.data.total}
          </span>
          <button
            className="btn"
            disabled={page * 10 >= result.data.total}
            onClick={() => move(page + 1)}
          >
            পরবর্তী
          </button>
        </div>
      </Card>
      <Card title="দিনভিত্তিক জানা সম্পূর্ণ সময় · Asia/Dhaka">
        <p>
          মধ্যরাত পার হলে সময় আলাদা দিনে ভাগ হয়েছে। শুধু জানা duration-এর দিন
          দেখানো হয়।
        </p>
        {s.daily.length ? (
          <table className="table">
            <caption>
              রেকর্ড করা ব্যক্তিগত সময়; পূর্ণ বিদ্যুৎ নির্ভরযোগ্যতার পরিসংখ্যান
              নয়
            </caption>
            <thead>
              <tr>
                <th>দিন</th>
                <th>জানা মিনিট</th>
              </tr>
            </thead>
            <tbody>
              {s.daily.map((d) => (
                <tr key={d.date}>
                  <td>{d.date}</td>
                  <td>{d.known_minutes.toLocaleString("bn-BD")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>দিনভিত্তিক duration দেখানোর মতো সম্পূর্ণ সময় নেই।</p>
        )}
      </Card>
    </>
  );
}
