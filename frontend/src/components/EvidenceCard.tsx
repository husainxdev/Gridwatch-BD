import type { ReactNode } from "react";
import { shortTime } from "../client";
import { Card } from "./ui";
export function EvidenceCard({
  title,
  type,
  publisher,
  source,
  verification,
  observedAt,
  updatedAt,
  updateLabel = "GridWatch রেকর্ডের সর্বশেষ পরিবর্তন",
  retrievedAt,
  scope,
  stale,
  children,
}: {
  title: string;
  type: string;
  publisher: string;
  source?: string | null;
  verification?: string;
  observedAt?: string | null;
  updatedAt?: string | null;
  updateLabel?: string;
  retrievedAt: string | null;
  scope: string;
  stale?: boolean;
  children: ReactNode;
}) {
  return (
    <Card title={title} className={`evidence-card ${stale ? "outdated" : ""}`}>
      <p className="eyebrow">{type}</p>
      <p className="hint">
        সূত্র:{" "}
        {source ? (
          <a href={source} target="_blank" rel="noreferrer">
            {publisher} · মূল উৎস ↗
          </a>
        ) : (
          publisher
        )}
      </p>
      {stale && (
        <p className="freshness-warning" role="status">
          তথ্য হালনাগাদ হয়নি — আগের তথ্য দেখানো হচ্ছে।
        </p>
      )}
      {children}
      <details className="evidence-details">
        <summary>উৎস, সময় ও সীমাবদ্ধতা দেখুন</summary>
        <dl className="evidence-facts">
          <div>
            <dt>উৎস / প্রকাশক</dt>
            <dd>
              {source ? (
                <a href={source} target="_blank" rel="noreferrer">
                  {publisher} · মূল উৎস ↗
                </a>
              ) : (
                publisher
              )}
            </dd>
          </div>
          {verification && (
            <div>
              <dt>GridWatch যাচাই</dt>
              <dd>{verification}</dd>
            </div>
          )}
          <div>
            <dt>প্রকাশ / পর্যবেক্ষণের সময়</dt>
            <dd>{observedAt ? shortTime(observedAt) : "সময় দেওয়া নেই"}</dd>
          </div>
          <div>
            <dt>{updateLabel}</dt>
            <dd>
              {updatedAt ? shortTime(updatedAt) : "আলাদা পরিবর্তনের সময় নেই"}
            </dd>
          </div>
          {source && (
            <div>
              <dt>মূল উৎসের আলাদা হালনাগাদের সময়</dt>
              <dd>কর্তৃপক্ষের আলাদা update time পাওয়া যায়নি।</dd>
            </div>
          )}
          <div>
            <dt>সর্বশেষ সফল তথ্য সংগ্রহ</dt>
            <dd>
              {retrievedAt ? shortTime(retrievedAt) : "এখনো সংগ্রহ হয়নি"}
            </dd>
          </div>
          <div>
            <dt>আওতা ও সীমাবদ্ধতা</dt>
            <dd>{scope}</dd>
          </div>
        </dl>
      </details>
    </Card>
  );
}
