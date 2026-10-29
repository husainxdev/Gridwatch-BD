"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section role="alert" className="card">
      <h1>পাতাটি খোলা যায়নি</h1>
      <p>আবার চেষ্টা করুন।</p>
      <button className="btn" onClick={reset}>
        আবার চেষ্টা করুন
      </button>
    </section>
  );
}
