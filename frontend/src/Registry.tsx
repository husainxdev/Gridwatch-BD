import { useEffect, useState, type FormEvent } from "react";
import { api, shortTime, type Page } from "./client";
import { Card } from "./components/ui";
import { LocationPicker } from "./components/LocationPicker";
import { AuditTrail, ListControls, useList, useRequest } from "./management";
import toast from "react-hot-toast";

type Record = {
  id: string;
  version: number;
  name_bn: string;
  name_en: string;
  source_url: string;
  verification_status: string;
  is_active: boolean;
  verified_at: string | null;
  feeder_name: string;
  coverage_description: string;
  office_id: string;
  location_id: string;
  office_name?: string;
  location_name?: string;
  usable?: boolean;
};
export function RegistryWorkspace({
  entity,
}: {
  entity: "offices" | "mappings";
}) {
  const [revision, setRevision] = useState(0);
  const list = useList<Record>(`/api/admin/registry/${entity}`, revision);
  const [edit, setEdit] = useState<Record | null>(null),
    [area, setArea] = useState(""),
    [office, setOffice] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const reload = () => setRevision((v) => v + 1);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const f = new FormData(e.currentTarget);
    const data =
      entity === "offices"
        ? { name_bn: f.get("name_bn"), name_en: f.get("name_en") }
        : {
            feeder_name: f.get("feeder_name"),
            coverage_description: f.get("coverage_description"),
            office_id: office,
            location_id: area,
          };
    if (entity === "mappings" && (!office || !area)) {
      setError("যাচাইকৃত অফিস ও এলাকা বাছুন।");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/registry/${entity}${edit ? `/${edit.id}` : ""}`, {
        method: edit ? "PUT" : "POST",
        body: JSON.stringify({
          ...data,
          source_url: f.get("source_url"),
          version: edit?.version || 1,
        }),
      });
      toast.success("যাচাই-বাকি রেকর্ড সংরক্ষিত");
      setEdit(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function action(r: Record, action: string) {
    if (busy) return;
    const reason =
      action === "delete"
        ? ""
        : prompt(
            "যাচাই / পরিবর্তনের কারণ ও কী প্রমাণ দেখেছেন লিখুন (কমপক্ষে ৫ অক্ষর)",
          );
    if (reason === null || (action !== "delete" && reason.trim().length < 5))
      return;
    if (
      !confirm(
        action === "delete"
          ? "শুধু কখনো যাচাই না-করা অব্যবহৃত খসড়া মুছবে। নিশ্চিত?"
          : action === "verify"
            ? "মূল উৎসে এই অফিস/feeder আওতা সরাসরি নিশ্চিত করেছেন? এটি আপনার source review, সরকারি endorsement নয়।"
            : "রেকর্ডের সক্রিয়তা বদলাবে; পুনরায় source review লাগবে। ইতিহাস থাকবে। নিশ্চিত?",
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      await api(
        `/api/admin/registry/${entity}/${r.id}${action === "delete" ? `?version=${r.version}` : `/${action}`}`,
        {
          method: action === "delete" ? "DELETE" : "POST",
          ...(action === "delete"
            ? {}
            : { body: JSON.stringify({ version: r.version, reason }) }),
        },
      );
      toast.success("পরিবর্তন সংরক্ষিত");
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <p>
        কেবল মূল উৎসে উল্লেখিত পরিচয় ও আওতা লিখুন। প্রশাসনিক এলাকা থেকে feeder
        অনুমান করবেন না। ডেমো বা বানানো অফিস/code যোগ করবেন না। এই registry নিজে
        কোনো schedule-এর আওতা বদলায় না।
      </p>
      <div className="admin-grid">
        <Card
          title={
            edit
              ? "Registry রেকর্ড সম্পাদনা"
              : entity === "offices"
                ? "বিদ্যুৎ অফিস যোগ"
                : "উৎসসহ feeder mapping যোগ"
          }
        >
          <form
            className="form-stack"
            onSubmit={submit}
            key={edit?.id || "new"}
          >
            <fieldset disabled={busy} className="form-stack">
              {entity === "offices" ? (
                <>
                  <label>
                    বাংলা নাম
                    <input
                      className="input"
                      name="name_bn"
                      defaultValue={edit?.name_bn}
                      minLength={2}
                      maxLength={160}
                      required
                    />
                  </label>
                  <label>
                    English name
                    <input
                      className="input"
                      name="name_en"
                      defaultValue={edit?.name_en}
                      minLength={2}
                      maxLength={160}
                      required
                    />
                  </label>
                </>
              ) : (
                <>
                  <OfficeSelector value={office} onChange={setOffice} />
                  <label>
                    উৎসে লেখা feeder নাম
                    <input
                      className="input"
                      name="feeder_name"
                      defaultValue={edit?.feeder_name}
                      minLength={2}
                      maxLength={160}
                      required
                    />
                  </label>
                  <LocationPicker value={area} onChange={setArea} />
                  <label>
                    উৎসে লেখা নির্দিষ্ট আওতা ও সীমাবদ্ধতা
                    <textarea
                      className="textarea"
                      name="coverage_description"
                      defaultValue={edit?.coverage_description}
                      minLength={12}
                      maxLength={1000}
                      required
                    />
                  </label>
                </>
              )}
              <label>
                মূল প্রমাণের HTTPS লিংক
                <input
                  className="input"
                  name="source_url"
                  type="url"
                  pattern="https://.*"
                  defaultValue={edit?.source_url}
                  required
                />
              </label>
              <p className="hint">
                সংরক্ষণে verified হয় না। সম্পাদনার পর আবার যাচাই দরকার। অফিস
                বদলালে তার mappings-ও যাচাই-বাকি হবে।
              </p>
              <button className="btn btn-primary" disabled={busy}>
                {busy ? "অপেক্ষা করুন…" : "খসড়া সংরক্ষণ"}
              </button>
              {edit && (
                <button
                  type="button"
                  className="btn"
                  onClick={() => setEdit(null)}
                >
                  সম্পাদনা বাতিল
                </button>
              )}
            </fieldset>
            {error && <p role="alert">{error}</p>}
          </form>
        </Card>
        <Card
          title={
            entity === "offices"
              ? "উৎসযুক্ত বিদ্যুৎ অফিস"
              : "পর্যালোচিত feeder mappings"
          }
        >
          <ListControls
            list={list}
            statuses={["verified", "unverified"]}
            dates={false}
          />
          <div className="toolbar">
            <label>
              সক্রিয়তা
              <select
                className="select"
                value={list.params.get("active") || ""}
                onChange={(e) => list.update("active", e.target.value)}
              >
                <option value="">সব</option>
                <option value="true">সক্রিয়</option>
                <option value="false">স্থগিত</option>
              </select>
            </label>
            {entity === "mappings" && (
              <>
                <label>
                  অফিসের ID
                  <input
                    className="input"
                    value={list.params.get("office_id") || ""}
                    onChange={(e) => list.update("office_id", e.target.value)}
                  />
                </label>
                <label>
                  এলাকার ID
                  <input
                    className="input"
                    value={list.params.get("location_id") || ""}
                    onChange={(e) => list.update("location_id", e.target.value)}
                  />
                </label>
              </>
            )}
          </div>
          {list.data?.items.map((r) => (
            <div key={r.id} className="record">
              <strong>
                {entity === "offices"
                  ? `${r.name_bn} · ${r.name_en}`
                  : r.feeder_name}
              </strong>
              <span>
                {r.verification_status} · {r.is_active ? "সক্রিয়" : "স্থগিত"} ·
                সংস্করণ {r.version}
              </span>
              {entity === "mappings" && (
                <>
                  <span>
                    {r.office_name} → {r.location_name}
                  </span>
                  <p>{r.coverage_description}</p>
                  <span>
                    {r.usable
                      ? "অফিস, এলাকা ও mapping-এর বর্তমান source review মেলে"
                      : "ব্যবহারের আগে অফিস, এলাকা ও mapping পুনরায় যাচাই দরকার"}
                  </span>
                </>
              )}
              <a href={r.source_url} target="_blank" rel="noreferrer">
                মূল উৎস ↗
              </a>
              <span>
                শেষ source review:{" "}
                {r.verified_at ? shortTime(r.verified_at) : "এখনো হয়নি"}
              </span>
              <div className="inline-actions">
                <button
                  className="btn btn-sm"
                  disabled={busy}
                  onClick={() => {
                    setEdit(r);
                    setOffice(r.office_id || "");
                    setArea(r.location_id || "");
                  }}
                >
                  সম্পাদনা
                </button>
                {r.is_active && r.verification_status !== "verified" && (
                  <button
                    className="btn btn-sm"
                    disabled={busy}
                    onClick={() => action(r, "verify")}
                  >
                    উৎস দেখে যাচাই
                  </button>
                )}
                <button
                  className="btn btn-sm"
                  disabled={busy}
                  onClick={() =>
                    action(r, r.is_active ? "deactivate" : "activate")
                  }
                >
                  {r.is_active ? "স্থগিত" : "সক্রিয় করুন"}
                </button>
                <button
                  className="btn btn-sm"
                  disabled={busy}
                  onClick={() => action(r, "delete")}
                >
                  খসড়া মুছুন
                </button>
              </div>
              <AuditTrail
                entity={
                  entity === "offices"
                    ? "electricity_offices"
                    : "feeder_mappings"
                }
                id={r.id}
              />
            </div>
          ))}
        </Card>
      </div>
    </>
  );
}
function OfficeSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
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
  const result = useRequest<Page<Record>>(
    `/api/admin/registry/offices?status=verified&active=true&search=${encodeURIComponent(query)}&page=${page}&page_size=10`,
  );
  return (
    <div>
      <label>
        যাচাইকৃত অফিস খুঁজুন
        <input
          className="input"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </label>
      <label>
        অফিস
        <select
          className="select"
          aria-label="অফিস"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
        >
          <option value="">বাছুন</option>
          {value && !result.data?.items.some((x) => x.id === value) && (
            <option value={value}>বর্তমান নির্বাচন · {value}</option>
          )}
          {result.data?.items.map((x) => (
            <option key={x.id} value={x.id}>
              {x.name_bn}
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
          আগের অফিস
        </button>
        <button
          type="button"
          className="btn btn-sm"
          disabled={!result.data || page * 10 >= result.data.total}
          onClick={() => setPage((p) => p + 1)}
        >
          পরের অফিস
        </button>
      </div>
    </div>
  );
}
