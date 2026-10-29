"use client";

import NextLink from "next/link";
import {
  usePathname,
  useRouter,
  useSearchParams as useNextSearchParams,
} from "next/navigation";
import { useCallback, useEffect, useMemo, type ComponentProps } from "react";

// Keep the existing component contracts while all navigation uses Next App Router.
type LinkProps = Omit<ComponentProps<typeof NextLink>, "href"> & { to: string };
export function Link({ to, ...props }: LinkProps) {
  return <NextLink href={to} {...props} />;
}
export function NavLink({
  to,
  end = false,
  className = "",
  ...props
}: LinkProps & { end?: boolean }) {
  const pathname = usePathname();
  const active = end
    ? pathname === to
    : pathname === to || pathname.startsWith(to + "/");
  return (
    <Link
      to={to}
      aria-current={active ? "page" : undefined}
      className={`${className}${active ? " active" : ""}`}
      {...props}
    />
  );
}
export function useNavigate() {
  const router = useRouter();
  return useCallback(
    (to: string, options?: { replace?: boolean }) => {
      // Call sites navigate internally; never accept an external or script URL.
      if (!to.startsWith("/") || to.startsWith("//") || to.includes("\\"))
        return;
      if (options?.replace) router.replace(to);
      else router.push(to);
    },
    [router],
  );
}
export function Navigate({
  to,
  replace = false,
}: {
  to: string;
  replace?: boolean;
}) {
  const navigate = useNavigate();
  useEffect(() => navigate(to, { replace }), [navigate, to, replace]);
  return (
    <div className="loading-state" role="status">
      পাতা খোলা হচ্ছে…
    </div>
  );
}
type QueryInput = URLSearchParams | Record<string, string>;
export function useSearchParams() {
  const current = useNextSearchParams();
  const query = current.toString();
  const params = useMemo(() => new URLSearchParams(query), [query]);
  const setParams = useCallback(
    (value: QueryInput | ((previous: URLSearchParams) => QueryInput)) => {
      // Next integrates native history updates with useSearchParams. Using the
      // current URL avoids losing rapid consecutive changes to separate filters.
      const previous = new URLSearchParams(window.location.search);
      const next = new URLSearchParams(
        typeof value === "function" ? value(previous) : value,
      );
      const suffix = next.toString();
      window.history.pushState(
        null,
        "",
        window.location.pathname +
          (suffix ? `?${suffix}` : "") +
          window.location.hash,
      );
    },
    [],
  );
  return [params, setParams] as const;
}
