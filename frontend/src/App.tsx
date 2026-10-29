import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink } from "./navigation";
import {
  FiActivity,
  FiArrowRight,
  FiBookOpen,
  FiClock,
  FiGrid,
  FiMapPin,
  FiRefreshCw,
  FiShield,
  FiZap,
} from "react-icons/fi";
import toast from "react-hot-toast";
import { fetchAreas, formatTime, type DemoArea } from "./api";
import { Card, EmptyState, EvidenceBadge } from "./components/ui";
import { useSession } from "./session";

export function Overview() {
  const [areas, setAreas] = useState<DemoArea[]>([]);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    fetchAreas(controller.signal)
      .then((items) => {
        setAreas(items);
        setSelected((current) =>
          items.some((a) => a.id === current) ? current : items[0]?.id || "",
        );
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [attempt]);
  const area = areas.find((a) => a.id === selected);
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">আপনার এলাকার বিদ্যুৎ তথ্য</p>
          <h1>
            আগে জানুন,
            <br className="mobile-break" /> প্রস্তুত থাকুন।
          </h1>
          <p>
            পরিকল্পিত বন্ধ, ব্যক্তিগত রিপোর্ট ও যাচাইকৃত ঘটনা — আলাদা করে দেখুন।
          </p>
        </div>
        <span className="pilot-tag">
          <span /> সিলেট পাইলট · প্রস্তুতি পর্ব
        </span>
      </div>
      <div className="demo-banner" role="note">
        <FiInfoIcon />
        <div>
          <strong>এটি একটি ডেমো পরিবেশ</strong>
          <p>
            এখানে কোনো লাইভ বা সরকারি বিদ্যুৎ তথ্য নেই। নমুনা এলাকাগুলো কেবল
            ইন্টারফেস প্রদর্শনের জন্য।
          </p>
        </div>
        <Link to="/sources">
          তথ্যের নীতি <FiArrowRight />
        </Link>
      </div>
      <section className="location-bar" aria-label="এলাকা নির্বাচন">
        <FiMapPin />
        <div>
          <label htmlFor="area">নমুনা এলাকা নির্বাচন</label>
          <select
            className="select"
            id="area"
            value={selected}
            disabled={loading || !!error || areas.length === 0}
            onChange={(e) => setSelected(e.target.value)}
          >
            {!areas.length && (
              <option value="">
                {loading ? "লোড হচ্ছে…" : "কোনো এলাকা নেই"}
              </option>
            )}
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name_bn}
              </option>
            ))}
          </select>
        </div>
        <span className="location-note">সময়: বাংলাদেশ (UTC+6)</span>
        <button
          className="btn btn-ghost"
          aria-label="তথ্য পুনরায় লোড করুন"
          onClick={() => setAttempt((n) => n + 1)}
          disabled={loading}
        >
          <FiRefreshCw />
        </button>
      </section>
      {loading ? (
        <div className="loading-state" role="status">
          <span className="loading loading-spinner" /> এলাকার তথ্য লোড হচ্ছে…
        </div>
      ) : error ? (
        <div className="alert alert-error" role="alert">
          <span>{error}</span>
          <button
            className="btn btn-sm"
            onClick={() => setAttempt((n) => n + 1)}
          >
            আবার চেষ্টা করুন
          </button>
        </div>
      ) : !area ? (
        <Card title="এলাকার তথ্য">
          <EmptyState title="নমুনা এলাকা যোগ করা হয়নি">
            সেটআপ নির্দেশনা অনুসারে ডেমো seed চালান।
          </EmptyState>
        </Card>
      ) : (
        <>
          <div className="overview-grid">
            <section className="status-card">
              <div className="status-top">
                <span>
                  <FiActivity /> সংযোগের অবস্থা
                </span>
                <EvidenceBadge>অজানা</EvidenceBadge>
              </div>
              <div className="status-symbol">
                <FiZap />
              </div>
              <h2>বর্তমান অবস্থা জানা নেই</h2>
              <p>
                যাচাইকৃত তথ্য নেই। রিপোর্ট না থাকা মানেই বিদ্যুৎ আছে — এমন নয়।
              </p>
              <div className="status-meta">
                <FiMapPin /> {area.name_bn}
                <span>ডেমো</span>
              </div>
            </section>
            <Card title="পরবর্তী ঘোষিত সময়সূচি" className="schedule-card">
              <EvidenceBadge>কোনো সরকারি তথ্য সংযুক্ত নেই</EvidenceBadge>
              <EmptyState title="যাচাইকৃত সময়সূচি নেই">
                সময়সূচি যোগ হলে মূল নোটিশের উৎস ও যাচাইয়ের অবস্থা এখানে দেখা
                যাবে।
              </EmptyState>
              <div className="card-foot">
                <FiClock /> নির্ধারিত সময় শেষ হওয়া বিদ্যুৎ ফেরার প্রমাণ নয়।
              </div>
            </Card>
          </div>
          <div className="detail-grid">
            <Card title="কমিউনিটির সাম্প্রতিক রিপোর্ট">
              <div className="section-subtitle">
                রিপোর্ট একজনের সংযোগের অভিজ্ঞতা জানায়।
              </div>
              <EmptyState title="এখনো কোনো রিপোর্ট নেই">
                ব্যক্তিগত রিপোর্ট দিতে লগইন করে ড্যাশবোর্ডে যান। এই ডেমোতে
                বাস্তব রিপোর্ট নেই।
              </EmptyState>
            </Card>
            <Card title="তথ্যের পরিচয়">
              <dl className="evidence-list">
                <div>
                  <dt>তথ্যের ধরন</dt>
                  <dd>প্রদর্শনী / ডেমো</dd>
                </div>
                <div>
                  <dt>উৎস</dt>
                  <dd>স্থানীয় development seed</dd>
                </div>
                <div>
                  <dt>যাচাই</dt>
                  <dd>বাস্তব এলাকার তথ্য নয়</dd>
                </div>
                <div>
                  <dt>নমুনা আপডেট</dt>
                  <dd>{formatTime(area.updated_at)}</dd>
                </div>
              </dl>
              <p className="fine-print">
                এটি নমুনা রেকর্ডের সময়; বিদ্যুৎ অবস্থার আপডেট নয়।
              </p>
            </Card>
          </div>
          <div className="next-panel">
            <div className="next-icon">
              <FiShield />
            </div>
            <div>
              <h2>বিশ্বস্ত তথ্য দিয়ে ছোট পরিসরে শুরু</h2>
              <p>
                পাইলটের সীমানা ও সরকারি উৎস যাচাইয়ের পর বাস্তব তথ্য যুক্ত হবে।
              </p>
            </div>
            <Link className="btn" to="/sources">
              কীভাবে যাচাই হবে <FiArrowRight />
            </Link>
          </div>
        </>
      )}
    </>
  );
}
function FiInfoIcon() {
  return <FiShield aria-hidden="true" />;
}
export function Sources() {
  return (
    <>
      <p className="eyebrow">স্বচ্ছতা ও আস্থা</p>
      <h1>তথ্যের উৎস ও সীমাবদ্ধতা</h1>
      <div className="reading">
        <Card title="সিলেট পাইলট: যাচাই এখনো বাকি">
          <p>
            কোনো বাস্তব ওয়ার্ড, পাড়া বা ফিডারকে এই সংস্করণে সমর্থিত বলে দাবি
            করা হচ্ছে না। সিলেটের একটি ছোট এলাকা বেছে নিয়ে প্রশাসনিক সীমানা,
            বিদ্যুৎ সরবরাহকারী ও প্রকাশ্য নোটিশের উৎস হাতে যাচাই করতে হবে।
          </p>
        </Card>
        <Card title="তিন ধরনের তথ্য, তিনটি অর্থ">
          <ul>
            <li>
              <strong>ঘোষিত সময়সূচি:</strong> মূল নোটিশে প্রকাশিত পরিকল্পনা;
              বাস্তব বিভ্রাটের প্রমাণ নয়।
            </li>
            <li>
              <strong>ব্যক্তিগত রিপোর্ট:</strong> একজন ব্যবহারকারীর সংযোগের
              অবস্থা; পুরো এলাকার সিদ্ধান্ত নয়।
            </li>
            <li>
              <strong>যাচাইকৃত ঘটনা:</strong> প্রমাণসহ পর্যালোচিত বিভ্রাট।
              পুনরুদ্ধারের জন্য আলাদা প্রমাণ লাগবে।
            </li>
          </ul>
        </Card>
        <Card title="এই সংস্করণে যা আছে">
          <p>
            এলাকা নির্বাচনের ডেমো, তথ্যের স্পষ্ট লেবেল, ডেটাবেস কাঠামো ও health
            API। লগইন, রিপোর্ট জমা, অ্যাডমিন ব্যবস্থাপনা ও কার্যক্রমের সময়
            মেলানো রয়েছে; যাচাইকৃত পাইলট এলাকা ও তথ্য যুক্ত না হওয়া পর্যন্ত
            বাস্তব ফল দেখাবে না। কোনো সরকারি API সংযুক্ত নেই।
          </p>
          <button
            className="btn btn-outline"
            onClick={() => {
              navigator.clipboard
                .writeText(window.location.href)
                .then(() => toast.success("লিংক কপি হয়েছে"))
                .catch(() => toast.error("লিংক কপি করা যায়নি"));
            }}
          >
            এই পাতার লিংক কপি করুন
          </button>
        </Card>
      </div>
    </>
  );
}
export function Roadmap() {
  return (
    <>
      <p className="eyebrow">নির্মাণের অগ্রগতি</p>
      <h1>স্বচ্ছভাবে, ধাপে ধাপে।</h1>
      <div className="reading">
        <Card title="ভিত্তি ও তথ্যের নীতি">
          <p>
            স্কোপ, তথ্যের নীতি, ডেটাবেস, migration, health API এবং এই অ্যাপ শেল
            তৈরি হয়েছে।
          </p>
        </Card>
        <Card title="কার্যকর ধাপ · অ্যাকাউন্ট ও তথ্যপ্রবাহ">
          <p>
            JWT access token, refresh cookie, bcrypt, লগআউট, password reset,
            এলাকা API, অ্যাডমিন অনুমতি, নোটিশ ও রিপোর্টের কার্যপ্রবাহ যুক্ত
            হয়েছে। SMTP ও যাচাইকৃত পাইলট উৎস সেট করতে হবে।
          </p>
        </Card>
        <Card title="প্রকাশের আগে">
          <p>
            অনুমতি ও তথ্যের নির্ভুলতা পরীক্ষা, মোবাইল ব্যবহারযোগ্যতা, যাচাইকৃত
            পাইলট উৎস এবং বাস্তব deployment যাচাই করতে হবে। সাত দিনের পরিকল্পনা
            কাজের নির্দেশনা; শেষ করার নিশ্চয়তা নয়।
          </p>
        </Card>
      </div>
    </>
  );
}
export default function App({ children }: { children: ReactNode }) {
  const { user, signOut } = useSession();
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        মূল তথ্যে যান
      </a>
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-icon">
            <FiZap />
          </span>
          <span>
            GridWatch <b>BD</b>
            <small>বিদ্যুতের খবর, আপনার পাশে</small>
          </span>
        </Link>
        <div className="nav-label">ওভারভিউ</div>
        <nav aria-label="প্রধান নেভিগেশন">
          <NavLink to="/" end>
            <FiGrid /> এলাকার তথ্য
          </NavLink>
          <NavLink to="/sources">
            <FiBookOpen /> উৎস ও তথ্যনীতি
          </NavLink>
          <NavLink to="/notices">
            <FiBookOpen /> নোটিশ
          </NavLink>
          <NavLink to="/dashboard">
            <FiActivity /> ড্যাশবোর্ড
          </NavLink>
          <NavLink to="/activities">কাজের সময়</NavLink>
          <NavLink to="/history">আমার ইতিহাস</NavLink>
          {user?.role === "admin" && (
            <NavLink to="/admin">
              <FiShield /> অ্যাডমিন
            </NavLink>
          )}
          <NavLink to="/progress">
            <FiActivity /> অগ্রগতি
          </NavLink>
        </nav>
        <div className="sidebar-bottom">
          <span className="badge">PILOT · v0.3</span>
          <p>
            বাংলাদেশের জন্য তৈরি
            <br />
            সিলেট থেকে শুরু
          </p>
          <span className="country-mark">●</span>
        </div>
      </aside>
      <div className="workspace">
        <header>
          <span>
            <FiMapPin /> বাংলাদেশ <span className="header-divider">/</span>{" "}
            সিলেট
          </span>
          <span className="language-tag">
            {user ? (
              <button
                className="btn btn-sm"
                onClick={() =>
                  signOut()
                    .then(() => toast.success("লগআউট হয়েছে"))
                    .catch((e) => toast.error(e.message))
                }
              >
                লগআউট
              </button>
            ) : (
              <Link to="/login">প্রবেশ</Link>
            )}{" "}
            বাংলা <span>BN</span>
          </span>
        </header>
        <main id="main">{children}</main>
        <footer>
          <span>© GridWatch BD · বিশ্ববিদ্যালয় প্রকল্প</span>
          <span>প্রদর্শনী সংস্করণ • জরুরি সেবা নয়</span>
        </footer>
      </div>
    </div>
  );
}
