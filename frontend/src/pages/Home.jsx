import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

const STEPS = [
  ["Open Jobright", "We open your Jobright job feed in the background."],
  ["Sign in", "Log in securely with Google, then your Jobright profile."],
  ["Extract live", "Direct company / ATS apply links stream in real time."],
  ["Download", "Export every link to Excel in one click."],
];

/* ---- Right-side animated mock screens (one per step) ---- */

function BrowserChrome({ url, children }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-xl">
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900 px-3 py-2">
        <span className="h-3 w-3 rounded-full bg-rose-500" />
        <span className="h-3 w-3 rounded-full bg-amber-400" />
        <span className="h-3 w-3 rounded-full bg-emerald-500" />
        <span className="ml-3 truncate rounded bg-slate-800 px-3 py-0.5 text-xs text-slate-400">
          {url}
        </span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function FrameJobright() {
  return (
    <BrowserChrome url="jobright.ai">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded bg-indigo-600 text-xs font-bold">
          JR
        </span>
        <span className="font-semibold">Jobright feed</span>
      </div>
      {["Data Analyst", "AI Engineer", "Backend Developer"].map((j, i) => (
        <div
          key={j}
          className="row-in mb-2 flex items-center justify-between rounded-lg bg-slate-900 px-3 py-2"
          style={{ animationDelay: `${i * 0.15}s` }}
        >
          <span className="text-sm text-slate-300">{j}</span>
          <span className="rounded-full bg-indigo-600 px-3 py-0.5 text-xs">Apply</span>
        </div>
      ))}
    </BrowserChrome>
  );
}

function FrameLogin() {
  return (
    <BrowserChrome url="accounts.google.com">
      <div className="mx-auto max-w-xs py-3 text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-slate-800 text-lg">
          G
        </div>
        <p className="font-semibold">Sign in</p>
        <div className="mt-4 space-y-2">
          <div className="row-in rounded-lg border border-slate-700 px-3 py-2 text-left text-xs text-slate-400">
            you@gmail.com
          </div>
          <div
            className="row-in rounded-lg border border-slate-700 px-3 py-2 text-left text-xs text-slate-500"
            style={{ animationDelay: "0.15s" }}
          >
            ••••••••
          </div>
          <div
            className="row-in rounded-lg bg-indigo-600 py-2 text-xs font-medium"
            style={{ animationDelay: "0.3s" }}
          >
            Continue
          </div>
        </div>
      </div>
    </BrowserChrome>
  );
}

function FrameExtract() {
  const links = [
    "ats.greenhouse.io/embed/job_app",
    "myworkdayjobs.com/careers/job",
    "career.icims.com/jobs/7783",
  ];
  return (
    <BrowserChrome url="link-extractor">
      <div className="mb-1 flex justify-between text-xs text-slate-400">
        <span>Extracting…</span>
        <span>7/10</span>
      </div>
      <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div className="bar-fill h-full rounded-full bg-indigo-500" />
      </div>
      {links.map((l, i) => (
        <div
          key={l}
          className="row-in mb-2 flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-xs"
          style={{ animationDelay: `${0.4 + i * 0.4}s` }}
        >
          <span className="text-emerald-400">✓</span>
          <span className="truncate text-indigo-300">{l}</span>
        </div>
      ))}
    </BrowserChrome>
  );
}

function FrameDownload() {
  return (
    <BrowserChrome url="link-extractor">
      <div className="py-6 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-600 text-2xl">
          ✓
        </div>
        <p className="font-semibold">10 links ready</p>
        <div className="row-in mx-auto mt-4 flex w-40 items-center justify-center gap-2 rounded-lg bg-emerald-600 py-2 text-sm font-medium">
          ⬇ links.xlsx
        </div>
      </div>
    </BrowserChrome>
  );
}

const FRAMES = [FrameJobright, FrameLogin, FrameExtract, FrameDownload];

function Walkthrough() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setActive((a) => (a + 1) % STEPS.length), 2800);
    return () => clearInterval(t);
  }, []);

  const Frame = FRAMES[active];

  return (
    <div className="grid items-center gap-10 md:grid-cols-2">
      {/* Left: steps */}
      <div className="space-y-3">
        {STEPS.map(([title, desc], i) => {
          const on = i === active;
          return (
            <button
              key={title}
              onClick={() => setActive(i)}
              className={
                "flex w-full items-start gap-4 rounded-xl border p-4 text-left transition-all " +
                (on
                  ? "border-indigo-500 bg-slate-900"
                  : "border-transparent bg-slate-900/40 opacity-60 hover:opacity-100")
              }
            >
              <span
                className={
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold " +
                  (on ? "bg-indigo-600" : "bg-slate-700")
                }
              >
                {i + 1}
              </span>
              <span>
                <span className="block font-semibold">{title}</span>
                <span className="mt-1 block text-sm text-slate-400">{desc}</span>
              </span>
            </button>
          );
        })}
      </div>

      {/* Right: animated frame (key forces re-animate on change) */}
      <div className="frame-enter" key={active}>
        <Frame />
      </div>
    </div>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const authed = !!localStorage.getItem("user");

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link to="/" className="flex items-center gap-2">
          <img src="/logo.png" alt="LinkPilot" className="h-8 w-8 invert" />
          <span className="text-lg font-bold tracking-tight">LinkPilot</span>
        </Link>
        <Link
          to={authed ? "/app" : "/login"}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500"
        >
          {authed ? "Open App" : "Sign in"}
        </Link>
      </header>

      {/* Hero */}
      <main className="mx-auto max-w-4xl px-6 py-20 text-center">
        <h1 className="text-5xl font-bold leading-tight tracking-tight">
          Extract real job application links,
          <span className="text-indigo-400"> not portals.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-400">
          Pulls direct company / ATS apply links from your job feed — skips
          LinkedIn, Glassdoor and other portals. Watch it work live, export to Excel.
        </p>
        <div className="mt-10 flex justify-center">
          <button
            onClick={() => navigate(authed ? "/app" : "/login")}
            className="rounded-xl bg-indigo-600 px-8 py-3 font-medium hover:bg-indigo-500"
          >
            Get Started
          </button>
        </div>
      </main>

      {/* How it works — split walkthrough (content left, animation right) */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <h2 className="mb-12 text-center text-3xl font-bold">How it works</h2>
        <Walkthrough />
      </section>

      {/* Sources section */}
      <section className="mx-auto max-w-5xl px-6 pb-28">
        <h2 className="mb-3 text-center text-3xl font-bold">Where we extract from</h2>
        <p className="mx-auto mb-12 max-w-2xl text-center text-slate-400">
          Today we extract from Jobright. LinkedIn is coming soon — then pull from
          both at once and export together.
        </p>

        <div className="grid gap-6 sm:grid-cols-2">
          {/* Jobright - active, clickable -> sign in -> extractor */}
          <button
            onClick={() => navigate(authed ? "/app" : "/login")}
            className="rounded-2xl border border-emerald-500/40 bg-slate-900 p-6 text-left transition-all hover:border-emerald-400 hover:bg-slate-800"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 font-bold">
                  JR
                </span>
                <span className="text-lg font-semibold">Jobright</span>
              </div>
              <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-medium text-emerald-300">
                Active
              </span>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              Live now — direct apply links extracted from your Jobright feed.
            </p>
            <span className="mt-4 inline-block text-sm font-medium text-emerald-300">
              {authed ? "Open extractor →" : "Sign in to start →"}
            </span>
          </button>

          {/* LinkedIn - coming soon (not clickable yet) */}
          <div className="cursor-not-allowed rounded-2xl border border-amber-500/30 bg-slate-900 p-6 opacity-60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#0a66c2] font-bold">
                  in
                </span>
                <span className="text-lg font-semibold">LinkedIn</span>
              </div>
              <span className="rounded-full bg-amber-500/20 px-3 py-1 text-xs font-medium text-amber-300">
                Coming soon
              </span>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              Soon — extract from Jobright + LinkedIn together, one export.
            </p>
          </div>
        </div>

        <div className="mt-14 text-center">
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
