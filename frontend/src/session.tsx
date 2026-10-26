import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, csrf, renewToken, setAccessToken, type User } from "./client";
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
    };
  }, []);
  async function signIn(email: string, password: string) {
    const result = await api<{ access_token: string; user: User }>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    );
    setAccessToken(result.access_token);
    setUser(result.user);
  }
  async function signUp(email: string, password: string, display_name: string) {
    const result = await api<{ access_token: string; user: User }>(
      "/api/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ email, password, display_name }),
      },
      false,
    );
    setAccessToken(result.access_token);
    setUser(result.user);
  }
  async function signOut() {
    try {
      if (csrf()) await api("/api/auth/logout", { method: "POST" }, false);
    } finally {
      setAccessToken(null);
      setUser(null);
    }
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
