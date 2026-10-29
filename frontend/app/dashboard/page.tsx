"use client";
import { RequireUser } from "../../src/pages";
import { Dashboard } from "../../src/pages";
export default function Page() {
  return (
    <RequireUser>
      <Dashboard />
    </RequireUser>
  );
}
