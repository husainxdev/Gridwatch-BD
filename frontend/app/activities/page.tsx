"use client";
import { RequireUser } from "../../src/pages";
import { ActivitiesPage } from "../../src/Planning";
export default function Page() {
  return (
    <RequireUser>
      <ActivitiesPage />
    </RequireUser>
  );
}
