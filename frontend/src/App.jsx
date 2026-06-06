import { useEffect, useRef, useState } from "react";

const API = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws/extract";

export default function App() {
  const [profile, setProfile] = useState("vamshi");
  const [maxLinks, setMaxLinks] = useState(31);
  const [headless, setHeadless] = useState(true);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [progress, setProgress] = useState({ saved: 0, max: 31 });
  const [links, setLinks] = useState([]);
  const [logs, setLogs] = useState([]);
  const wsRef = useRef(null);
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const addLog = (line) =>
    setLogs((l) => [...l, `${new Date().toLocaleTimeString()}  ${line}`]);

  const start = () => {
    setLinks([]);
    setLogs([]);
    setProgress({ saved: 0, max: Number(maxLinks) });
    setRunning(true);
    setStatus("Connecting...");

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("Running");
      ws.send(
        JSON.stringify({ profile, max_links: Number(maxLinks), headless })
      );
    };

    ws.onmessage = (e) => {
      const { type, payload } = JSON.parse(e.data);
      switch (type) {
        case "status":
          setStatus(payload.message || "Running");
          addLog("• " + (payload.message || ""));
          if (Array.isArray(payload.links) && payload.links.length) {
            setLinks((prev) => {
              const seen = new Set(prev.map((x) => x.url));
              const add = payload.links
                .filter((u) => !seen.has(u))
                .map((u) => ({ url: u, source: "resumed" }));
              return [...prev, ...add];
            });
          }
          break;
        case "progress":
          setProgress({ saved: payload.saved, max: payload.max });
          break;
        case "link":
          setLinks((prev) => [...prev, { url: payload.url, source: "new" }]);
          setProgress({ saved: payload.index, max: payload.max });
          addLog(`✓ saved (${payload.index}/${payload.max}) ${payload.url}`);
          break;
        case "skip":
          addLog(`↷ skip [${payload.reason}] ${payload.url || ""}`);
          break;
        case "error":
          addLog("⚠ " + payload.message);
          break;
        case "stopped":
          setStatus("Stopped");
          addLog("■ stopped by user");
          break;
        case "done":
          setStatus(`Done — ${payload.saved} new, ${payload.total} total`);
          addLog(`✔ done. new=${payload.saved} total=${payload.total}`);
          setRunning(false);
          ws.close();
          break;
        default:
          break;
      }
    };

    ws.onclose = () => setRunning(false);
    ws.onerror = () => {
      addLog("⚠ websocket error — is the API running on :8000?");
      setStatus("Error");
      setRunning(false);
    };
  };

  const stop = () => {
    wsRef.current?.send(JSON.stringify({ action: "stop" }));
    setStatus("Stopping...");
  };

  const pct = progress.max ? Math.round((progress.saved / progress.max) * 100) : 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">
            Jobright Link Extractor
          </h1>
          <p className="text-slate-400">
            Extract external job application links live.
          </p>
        </header>

        {/* Controls */}
        <div className="grid gap-4 rounded-2xl bg-slate-900 p-6 shadow-lg md:grid-cols-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Chrome profile</span>
            <input
              className="rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
              disabled={running}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Max links</span>
            <input
              type="number"
              min="1"
              className="rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
              value={maxLinks}
              onChange={(e) => setMaxLinks(e.target.value)}
              disabled={running}
            />
          </label>
          <label className="flex items-end gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={headless}
              onChange={(e) => setHeadless(e.target.checked)}
              disabled={running}
            />
            <span className="text-slate-400">Headless</span>
          </label>
          <div className="flex items-end gap-2">
            {!running ? (
              <button
                onClick={start}
                className="w-full rounded-lg bg-indigo-600 px-4 py-2 font-medium hover:bg-indigo-500"
              >
                Start
              </button>
            ) : (
              <button
                onClick={stop}
                className="w-full rounded-lg bg-rose-600 px-4 py-2 font-medium hover:bg-rose-500"
              >
                Stop
              </button>
            )}
          </div>
        </div>

        {/* Status + progress */}
        <div className="mt-6 rounded-2xl bg-slate-900 p-6">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-slate-300">
              Status: <span className="font-medium text-indigo-400">{status}</span>
            </span>
            <span className="text-slate-400">
              {progress.saved}/{progress.max}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-indigo-500 transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {/* Links table */}
          <div className="rounded-2xl bg-slate-900 p-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">Links ({links.length})</h2>
              <a
                href={`${API}/download`}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium hover:bg-emerald-500"
              >
                Download Excel
              </a>
            </div>
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-900 text-slate-400">
                  <tr>
                    <th className="py-2 pr-2">#</th>
                    <th className="py-2 pr-2">URL</th>
                    <th className="py-2">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {links.map((l, i) => (
                    <tr key={i} className="border-t border-slate-800">
                      <td className="py-2 pr-2 text-slate-500">{i + 1}</td>
                      <td className="py-2 pr-2">
                        <a
                          href={l.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-indigo-400 hover:underline break-all"
                        >
                          {l.url}
                        </a>
                      </td>
                      <td className="py-2">
                        <span
                          className={
                            l.source === "new"
                              ? "rounded bg-indigo-500/20 px-2 py-0.5 text-xs text-indigo-300"
                              : "rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300"
                          }
                        >
                          {l.source}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {links.length === 0 && (
                    <tr>
                      <td colSpan="3" className="py-6 text-center text-slate-500">
                        No links yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Live log */}
          <div className="rounded-2xl bg-slate-900 p-6">
            <h2 className="mb-3 font-semibold">Live log</h2>
            <div className="max-h-96 overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-300">
              {logs.length === 0 && (
                <p className="text-slate-600">Waiting to start...</p>
              )}
              {logs.map((line, i) => (
                <div key={i} className="whitespace-pre-wrap">
                  {line}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
