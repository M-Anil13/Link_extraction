import { Link, useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();
  const authed = !!localStorage.getItem("user");

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="text-lg font-bold tracking-tight">🔎 Jobright Extractor</span>
        {authed ? (
          <Link
            to="/app"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500"
          >
            Open App
          </Link>
        ) : (
          <Link
            to="/login"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500"
          >
            Sign in
          </Link>
        )}
      </header>

      {/* Hero */}
      <main className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="text-5xl font-bold leading-tight tracking-tight">
          Extract real job application links,
          <span className="text-indigo-400"> not portals.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-400">
          Pulls direct company / ATS apply links from your Jobright feed —
          skips LinkedIn, Glassdoor and other portals. Watch it work live,
          export to Excel.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <button
            onClick={() => navigate(authed ? "/app" : "/login")}
            className="rounded-xl bg-indigo-600 px-8 py-3 font-medium hover:bg-indigo-500"
          >
            Get Started
          </button>
        </div>

        {/* Feature cards */}
        <div className="mt-20 grid gap-6 text-left sm:grid-cols-3">
          {[
            ["Live extraction", "Stream each link as it's found, with progress."],
            ["Portal filtering", "Keeps direct ATS links, drops job portals."],
            ["Excel export", "Download all extracted links in one click."],
          ].map(([t, d]) => (
            <div key={t} className="rounded-2xl bg-slate-900 p-6">
              <h3 className="font-semibold text-indigo-300">{t}</h3>
              <p className="mt-2 text-sm text-slate-400">{d}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
