"use client";
import { RequireUser } from "../../src/pages";
import { Admin } from "../../src/pages";
export default function Page() {
  return (
    <RequireUser admin>
      <Admin />
    </RequireUser>
  );
}
