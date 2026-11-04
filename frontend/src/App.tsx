import type { ReactNode } from "react";
import { Link, NavLink } from "./navigation";
import {
  FiActivity,
  FiBookOpen,
  FiGrid,
  FiMapPin,
  FiShield,
  FiZap,
} from "react-icons/fi";
import toast from "react-hot-toast";
import { Card } from "./components/ui";
import { useSession } from "./session";

export { Overview } from "./Overview";

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
            অ্যাকাউন্ট, সংরক্ষিত এলাকা, নিজের সংযোগের রিপোর্ট, ঘোষণার জীবনচক্র,
            কাজের সময়ের মিল এবং ব্যক্তিগত ইতিহাস ব্যবহার করা যায়। Admin-এর
            পরিবর্তনে version check ও audit থাকে। সরকারি live API সংযুক্ত নেই;
            বাস্তব তথ্য আসল notice হাতে যাচাই করে প্রকাশ করতে হবে।
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
  const capabilities = [
    [
      "অ্যাকাউন্ট ও নিরাপত্তা",
      "নিবন্ধন, login, refresh, logout, role/ownership এবং password reset-এর workflow আছে। বহিরাগত email delivery আলাদা করে যাচাই করতে হবে।",
      "/login",
    ],
    [
      "এলাকা ও সংরক্ষণ",
      "প্রশাসনিক hierarchy, Bangla/English/alias search, একাধিক saved area ও একটি default। প্রশাসনিক এলাকা থেকে feeder অনুমান করা হয় না।",
      "/dashboard",
    ],
    [
      "নোটিশ ও ঘোষণা",
      "মূল উৎসসহ draft, review, publication, revision ও cancellation। ব্যক্তিগত রিপোর্ট থেকে ঘোষিত schedule তৈরি হয় না।",
      "/notices",
    ],
    [
      "ব্যক্তিগত সংযোগ",
      "Off, back ও still-off observation; একই request-এর retry আরেকটি outage তৈরি করে না।",
      "/dashboard",
    ],
    [
      "কাজের সময়",
      "সংরক্ষিত activity ও বর্তমান ঘোষণার overlap; overlapping সময় একবার গণনা এবং শেষ boundary-তে overlap নেই।",
      "/activities",
    ],
    [
      "নিজের ইতিহাস",
      "রেকর্ডভিত্তিক duration, Bangladesh daily split, range clipping এবং অজানা/open সময় আলাদা।",
      "/history",
    ],
  ];
  return (
    <>
      <p className="eyebrow">সক্ষমতা ও সীমাবদ্ধতা</p>
      <h1>কী ব্যবহার করতে পারবেন, কী এখনও বাকি</h1>
      <p>
        ফিচার চালু থাকা, বাস্তব বিদ্যুৎ তথ্য থাকা এবং online deployment—তিনটি
        আলাদা বিষয়। নিচের তালিকা কোনো production-readiness সনদ নয়।
      </p>
      <div className="home-notices">
        {capabilities.map(([title, description, route]) => (
          <Card key={title} title={title}>
            <p>{description}</p>
            <Link className="btn btn-outline" to={route}>
              খুলুন →
            </Link>
          </Card>
        ))}
      </div>
      <div className="reading">
        <Card title="স্থানীয়ভাবে যা যাচাই হয়েছে">
          <p>
            বাস্তব PostgreSQL-এ login/অনুমতি, refresh/logout, independent
            reports, interval/history calculations ও migration পরীক্ষা হয়েছে।
            Chromium-এ mobile/desktop, keyboard এবং automated accessibility
            checks হয়েছে; সব browser বা screen reader-এর certification নয়।
          </p>
        </Card>
        <Card title="প্রকাশের আগে এখনও যা দরকার">
          <ul>
            <li>
              একটি বাস্তব Sylhet এলাকার প্রশাসনিক সীমানা, বিদ্যুৎ সরবরাহকারী ও
              মূল notice যাচাই।
            </li>
            <li>
              আসল HTTPS frontend/backend URL, hosted cookies/CSRF, persistence,
              backup ও core journeys যাচাই।
            </li>
            <li>
              অনুমোদিত SMTP sender দিয়ে নিয়ন্ত্রিত recipient-এ delivery
              পরীক্ষা এবং public ingress rate protection।
            </li>
          </ul>
          <Link to="/sources">উৎস ও তথ্যের সীমা দেখুন →</Link>
        </Card>
        <Card title="ডেমো পরিবেশের অর্থ">
          <p>
            আলাদা demo database-এর সব এলাকা, review status, schedule, report ও
            event কাল্পনিক। পুরোনো পর্যবেক্ষণের সময় নিজে থেকে বদলায় না। সরকারি
            data বা সম্পূর্ণ monitoring হিসেবে ব্যবহার করবেন না।
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
            <FiActivity /> সেবার অবস্থা
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
        {process.env.NEXT_PUBLIC_DEMO_INSTANCE === "true" && (
          <p className="demo-banner" role="note">
            বিচ্ছিন্ন অনুশীলন পরিবেশ — সব ডেমো এলাকা, সময়সূচি ও ঘটনা কাল্পনিক;
            বাস্তব বিদ্যুৎ তথ্য নয়। ব্যক্তিগত তথ্য দেবেন না।
          </p>
        )}
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
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <footer>
          <span>© GridWatch BD · বিশ্ববিদ্যালয় প্রকল্প</span>
          <span>প্রদর্শনী সংস্করণ • জরুরি সেবা নয়</span>
        </footer>
      </div>
    </div>
  );
}
