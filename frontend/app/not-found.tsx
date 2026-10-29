import Link from "next/link";
export default function NotFound() {
  return (
    <section className="card">
      <h1>পাতাটি পাওয়া যায়নি</h1>
      <Link href="/" className="btn">
        মূল পাতায় ফিরুন
      </Link>
    </section>
  );
}
