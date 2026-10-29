import type { ReactNode } from "react";
import { FiInfo } from "react-icons/fi";
export function Card({
  title,
  children,
  className = "",
  headingLevel = 2,
}: {
  title: string;
  children: ReactNode;
  className?: string;
  headingLevel?: 1 | 2;
}) {
  const Heading = headingLevel === 1 ? "h1" : "h2";
  return (
    <section className={`panel ${className}`}>
      <Heading>{title}</Heading>
      {children}
    </section>
  );
}
export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <FiInfo aria-hidden="true" />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function EvidenceBadge({ children }: { children: ReactNode }) {
  return <span className="badge evidence-badge">{children}</span>;
}
