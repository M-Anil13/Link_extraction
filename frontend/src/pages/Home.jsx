import { Link, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";

// Reveal children when the section scrolls into view (one-shot).
function useReveal() {
  const ref = useRef(null);
  const [show, setShow] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShow(true);
          obs.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return [ref, show];
}

const STEPS = [
  ["1", "Sign in", "Log in with Google, then enter your Jobright profile."],
  ["2", "Extract live", "Watch links stream in real time as it scans your feed."],
  ["3", "Download", "Export every direct apply link to Excel in one click."],
];

export default function Home() {
  const navigate = useNavigate();
  const authed = !!localStorage.getItem("user");
  const [stepsRef, stepsShow] = useReveal();

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

      {/* How it works — animated step pipeline */}
      <section ref={stepsRef} className="mx-auto max-w-5xl px-6 pb-28">
        <h2 className="mb-16 text-center text-3xl font-bold">How it works</h2>

        <div className="flex flex-col items-stretch gap-6 md:flex-row md:items-center">
          {STEPS.map(([num, title, desc], i) => (
            <div key={num} className="flex flex-1 flex-col md:flex-row md:items-center">
              {/* Step card */}
              <div
                className={`reveal ${stepsShow ? "show" : ""} flex-1 rounded-2xl bg-slate-900 p-6 text-center`}
                style={{ animationDelay: `${i * 0.25}s` }}
              >
                <div
                  className={`pulse-badge mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-lg font-bold`}
                >
                  {num}
                </div>
                <h3 className="mt-4 font-semibold text-indigo-300">{title}</h3>
                <p className="mt-2 text-sm text-slate-400">{desc}</p>
              </div>

              {/* Animated connector (not after last step). Opacity via transition
                  so it doesn't override the 'flow' gradient animation. */}
              {i < STEPS.length - 1 && (
                <div
                  className="connector my-3 h-1 w-full rounded-full md:my-0 md:mx-3 md:w-16"
                  style={{
                    opacity: stepsShow ? 1 : 0,
                    transition: "opacity 0.6s ease",
                    transitionDelay: `${i * 0.25 + 0.15}s`,
                  }}
                />
              )}
            </div>
          ))}
        </div>

        <div className="mt-16 text-center">
          <button
            onClick={() => navigate(authed ? "/app" : "/login")}
            className="rounded-xl bg-indigo-600 px-8 py-3 font-medium hover:bg-indigo-500"
          >
            Try it now
          </button>
        </div>
      </section>
    </div>
  );
}
