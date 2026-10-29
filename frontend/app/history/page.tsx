"use client";
import { RequireUser } from "../../src/pages";
import { HistoryPage } from "../../src/Planning";
export default function Page() {
  return (
    <RequireUser>
      <HistoryPage />
    </RequireUser>
  );
}
