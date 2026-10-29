"use client";
import { useEffect, useState, type ReactNode } from "react";
import { Toaster } from "react-hot-toast";
import App from "../src/App";
import { SessionProvider } from "../src/session";
import * as client from "../src/client";
import { pollInterval } from "../src/polling";

declare global {
  interface Window {
    __gridwatchTest?: Pick<
      typeof client,
      "api" | "acceptSession" | "withSessionLock" | "localInputTime"
    > & { pollInterval: number };
  }
}
export default function Providers({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    // Opt-in only for the isolated browser runner; no tokens or storage getters.
    if (process.env.NEXT_PUBLIC_E2E_TEST === "1") {
      window.__gridwatchTest = {
        api: client.api,
        localInputTime: client.localInputTime,
        acceptSession: client.acceptSession,
        withSessionLock: client.withSessionLock,
        pollInterval,
      };
    }
    setMounted(true);
    return () => {
      delete window.__gridwatchTest;
    };
  }, []);
  // Session state is client-only. Server HTML and initial hydration agree,
  // and no private screen is rendered before refresh completes.
  if (!mounted)
    return (
      <main className="loading-state" role="status">
        GridWatch BD লোড হচ্ছে…
      </main>
    );
  return (
    <SessionProvider>
      <App>{children}</App>
      <Toaster position="bottom-center" />
    </SessionProvider>
  );
}
