import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";
import Providers from "./providers";
import "@fontsource/noto-sans-bengali/400.css";
import "@fontsource/noto-sans-bengali/600.css";
import "@fontsource/noto-sans-bengali/700.css";
import "../src/styles.css";

export const metadata: Metadata = {
  title: "GridWatch BD — বিদ্যুতের খবর",
  description:
    "ঘোষিত বিদ্যুৎ বন্ধ, ব্যক্তিগত রিপোর্ট ও যাচাইকৃত ঘটনার বাংলাদেশভিত্তিক বিশ্ববিদ্যালয় প্রকল্প।",
};
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="bn" data-theme="light">
      <body>
        <Suspense
          fallback={
            <main className="loading-state">GridWatch BD লোড হচ্ছে…</main>
          }
        >
          <Providers>{children}</Providers>
        </Suspense>
      </body>
    </html>
  );
}
