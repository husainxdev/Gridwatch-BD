import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  csrf,
  renewToken,
  acceptSession,
  announceSignOut,
  withSessionLock,
  type User,
} from "./client";
type Session = {
  user: User | null;
  checking: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (
    email: string,
    password: string,
    display_name: string,
  ) => Promise<void>;
  signOut: () => Promise<void>;
};
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [checking, setChecking] = useState(true);
  useEffect(() => {
    let active = true;
    const clear = () => setUser(null);
    const updated = (e: Event) => setUser((e as CustomEvent<User>).detail);
    window.addEventListener("gridwatch-session-updated", updated);
    window.addEventListener("gridwatch-session-ended", clear);
    renewToken()
      .then((result) => {
        if (active) {
          setUser(result.user);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setChecking(false);
      });
    return () => {
      active = false;
      window.removeEventListener("gridwatch-session-ended", clear);
      window.removeEventListener("gridwatch-session-updated", updated);
    };
  }, []);
  async function signIn(email: string, password: string) {
    return withSessionLock(async () => {
      const result = await api<{ access_token: string; user: User }>(
        "/api/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
        false,
      );
      acceptSession(result);
      setUser(result.user);
    });
  }
  async function signUp(email: string, password: string, display_name: string) {
    return withSessionLock(async () => {
      const result = await api<{ access_token: string; user: User }>(
        "/api/auth/register",
        {
          method: "POST",
          body: JSON.stringify({ email, password, display_name }),
        },
        false,
      );
      acceptSession(result);
      setUser(result.user);
    });
  }
  async function signOut() {
    if (!csrf())
      throw new Error(
        "Session cookie missing. Reload to verify session status.",
      );
    await withSessionLock(async () => {
      await api("/api/auth/logout", { method: "POST" }, false);
      announceSignOut();
      setUser(null);
    });
  }
  return (
    <Context.Provider value={{ user, checking, signIn, signUp, signOut }}>
      {children}
    </Context.Provider>
  );
}
export function useSession() {
  const value = useContext(Context);
  if (!value) throw Error("Session provider missing");
  return value;
}
