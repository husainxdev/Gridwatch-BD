import { useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useCurrentPath } from "./navigation";
import {
  FiActivity,
  FiBookOpen,
  FiCalendar,
  FiClock,
  FiGrid,
  FiHelpCircle,
  FiMenu,
  FiShield,
  FiX,
  FiZap,
} from "react-icons/fi";
import toast from "react-hot-toast";
import { useSession } from "./session";

export { Overview } from "./Overview";
export { Sources, Help as Roadmap } from "./SitePages";

export default function App({ children }: { children: ReactNode }) {
  const { user, checking, signOut } = useSession();
  const menuToggle = useRef<HTMLButtonElement>(null);
  const [openFor, setOpenFor] = useState<string | null>(null);
  const currentPath = useCurrentPath();
  const menuOpen = openFor === currentPath;
  const [signingOut, setSigningOut] = useState(false);
  async function logout() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await signOut();
      toast.success("লগআউট হয়েছে");
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setSigningOut(false);
    }
  }
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        মূল তথ্যে যান
      </a>
      <aside className="sidebar">
        <div className="brand-row">
          <Link to="/" className="brand" aria-label="GridWatch BD — হোম">
            <span className="brand-icon">
              <FiZap aria-hidden="true" />
            </span>
            <span>
              GridWatch <b>BD</b>
              <small>বিদ্যুতের খবর, আপনার পাশে</small>
            </span>
          </Link>
          <button
            className="menu-toggle btn btn-ghost"
            ref={menuToggle}
            aria-expanded={menuOpen}
            aria-controls="site-navigation"
            aria-label={menuOpen ? "মেনু বন্ধ করুন" : "মেনু খুলুন"}
            onClick={() => setOpenFor(menuOpen ? null : currentPath)}
          >
            {menuOpen ? (
              <FiX aria-hidden="true" />
            ) : (
              <FiMenu aria-hidden="true" />
            )}
          </button>
        </div>
        <div className="nav-label">আপনার বিদ্যুতের খবর</div>
        <nav
          id="site-navigation"
          className={menuOpen ? "site-navigation expanded" : "site-navigation"}
          aria-label="প্রধান নেভিগেশন"
          onClick={(event) => {
            if ((event.target as HTMLElement).closest("a")) setOpenFor(null);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape" && menuOpen) {
              setOpenFor(null);
              menuToggle.current?.focus();
            }
          }}
        >
          <NavLink to="/" end>
            <FiGrid aria-hidden="true" /> এলাকার তথ্য
          </NavLink>
          <NavLink to="/notices">
            <FiBookOpen aria-hidden="true" /> নোটিশ
          </NavLink>
          <NavLink to="/dashboard">
            <FiActivity aria-hidden="true" /> ড্যাশবোর্ড
          </NavLink>
          <NavLink to="/activities" className="secondary-route">
            <FiCalendar aria-hidden="true" /> কাজের সময়
          </NavLink>
          <NavLink to="/history" className="secondary-route">
            <FiClock aria-hidden="true" /> আমার ইতিহাস
          </NavLink>
          <NavLink to="/sources" className="secondary-route">
            <FiShield aria-hidden="true" /> উৎস ও তথ্যনীতি
          </NavLink>
          <NavLink to="/help" className="secondary-route">
            <FiHelpCircle aria-hidden="true" /> ব্যবহার নির্দেশনা
          </NavLink>
          {user?.role === "admin" && (
            <NavLink to="/admin" className="secondary-route">
              <FiShield aria-hidden="true" /> অ্যাডমিন
            </NavLink>
          )}
        </nav>
        <div className="sidebar-bottom">
          <span className="service-label">বাংলাদেশের জন্য তৈরি</span>
          <p>
            ঘোষণা, ব্যক্তিগত রিপোর্ট ও<br />
            যাচাইকৃত তথ্য—আলাদা করে জানুন।
          </p>
          <Link to="/privacy">গোপনীয়তা সম্পর্কে জানুন →</Link>
        </div>
      </aside>
      <div className="workspace">
        {process.env.NEXT_PUBLIC_DEMO_INSTANCE === "true" && (
          <p className="demo-banner" role="note">
            বিচ্ছিন্ন অনুশীলন পরিবেশ — সব ডেমো এলাকা, সময়সূচি ও ঘটনা কাল্পনিক;
            বাস্তব বিদ্যুৎ তথ্য নয়। ব্যক্তিগত তথ্য দেবেন না।
          </p>
        )}
        <header className="site-header">
          <span className="header-context">
            <span className="country-dot" aria-hidden="true" /> বিদ্যুৎ তথ্য ও
            কমিউনিটি রিপোর্ট
          </span>
          <div className="account-actions">
            {checking ? (
              <span role="status">সেশন যাচাই হচ্ছে…</span>
            ) : user ? (
              <>
                <span className="account-name">{user.display_name}</span>
                <button
                  className="btn btn-sm btn-outline"
                  disabled={signingOut}
                  onClick={() => void logout()}
                >
                  {signingOut ? "লগআউট হচ্ছে…" : "লগআউট"}
                </button>
              </>
            ) : (
              <>
                <Link className="account-login" to="/login">
                  প্রবেশ
                </Link>
                <Link className="btn btn-sm btn-primary" to="/register">
                  অ্যাকাউন্ট খুলুন
                </Link>
              </>
            )}
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <footer className="site-footer">
          <div>
            <strong>GridWatch BD</strong>
            <p>
              তথ্য বুঝে পরিকল্পনা করুন। নিরাপত্তার ঝুঁকিতে বিদ্যুৎ সরবরাহকারী বা
              জরুরি সেবার সঙ্গে যোগাযোগ করুন।
            </p>
          </div>
          <nav aria-label="সহায়তা ও নীতিমালা">
            <Link to="/help">সাহায্য</Link>
            <Link to="/sources">তথ্যের উৎস</Link>
            <Link to="/privacy">গোপনীয়তা</Link>
          </nav>
          <small>
            সরাসরি বিদ্যুৎ সরবরাহকারী বা জরুরি অভিযোগ গ্রহণের সেবা নয়।
          </small>
        </footer>
      </div>
    </div>
  );
}
