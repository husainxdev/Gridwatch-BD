import { useEffect } from "react";
export function SavedPager({
  page,
  total,
  loading,
  onChange,
}: {
  page: number;
  total: number;
  loading: boolean;
  onChange: (page: number) => void;
}) {
  useEffect(() => {
    if (!loading && total >= 0 && page > Math.max(1, Math.ceil(total / 100)))
      onChange(Math.max(1, Math.ceil(total / 100)));
  }, [page, total, loading, onChange]);
  if (total <= 100) return null;
  return (
    <nav aria-label="সংরক্ষিত এলাকার পৃষ্ঠা" className="inline-actions">
      <button
        type="button"
        className="btn btn-sm"
        disabled={page <= 1 || loading}
        onClick={() => onChange(page - 1)}
      >
        আগের সংরক্ষিত তালিকা
      </button>
      <span>
        পৃষ্ঠা {page} / {Math.ceil(total / 100)}
      </span>
      <button
        type="button"
        className="btn btn-sm"
        disabled={page * 100 >= total || loading}
        onClick={() => onChange(page + 1)}
      >
        আরও সংরক্ষিত এলাকা
      </button>
    </nav>
  );
}
