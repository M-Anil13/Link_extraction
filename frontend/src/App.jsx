import { useEffect, useRef, useState } from "react";

// Backend URL: set VITE_API_URL in Vercel (e.g. https://your-backend.onrender.com).
// Falls back to localhost for local dev. WS URL is derived (http->ws, https->wss).
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_URL = API.replace(/^http/, "ws") + "/ws/extract";

export default function App() {
  const [profile, setProfile] = useState("");
  const [maxLinks, setMaxLinks] = useState(31);
  const [headless, setHeadless] = useState(true);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [progress, setProgress] = useState({ saved: 0, max: 31 });
  const [links, setLinks] = useState([]);
  const [logs, setLogs] = useState([]);
  const [needLogin, setNeedLogin] = useState(false);
  const [frame, setFrame] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const wsRef = useRef(null);
  const logEndRef = useRef(null);
  const imgRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const sendInput = (obj) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(obj));
    }
  };

  // Map a click on the streamed frame back to page coordinates (frame is 1280x800).
  const onFrameClick = (e) => {
    const img = imgRef.current;
    if (!img) return;
    const rect = img.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * img.naturalWidth;
    const y = ((e.clientY - rect.top) / rect.height) * img.naturalHeight;
    sendInput({ type: "click", x: Math.round(x), y: Math.round(y) });
  };

  // Forward keystrokes while the login panel is active.
  useEffect(() => {
    if (!needLogin) return;
    const onKey = (e) => {
      if (e.key.length === 1) {
        sendInput({ type: "char", value: e.key });
      } else {
        sendInput({ type: "key", value: e.key }); // Enter/Backspace/Tab/Arrow*
      }
      if (["Tab", "Backspace", " ", "Enter", "ArrowUp", "ArrowDown"].includes(e.key))
        e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [needLogin]);

  const addLog = (line) =>
    setLogs((l) => [...l, `${new Date().toLocaleTimeString()}  ${line}`]);

  const start = () => {
    if (!profile.trim()) return; // profile required
    setLinks([]);
    setLogs([]);
    setNeedLogin(false);
    setFrame(null);
    setDownloadUrl(null);
    setProgress({ saved: 0, max: Number(maxLinks) });
    setRunning(true);
    setStatus("Connecting...");

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("Running");
      let email = null;
      try {
        email = JSON.parse(localStorage.getItem("user") || "{}").email || null;
      } catch {
        email = null;
      }
      ws.send(
        JSON.stringify({
          profile,
          max_links: Number(maxLinks),
          headless,
          interactive: true,
          email,
        })
      );
    };

    ws.onmessage = (e) => {
      const { type, payload } = JSON.parse(e.data);
      switch (type) {
        case "session":
          setDownloadUrl(API + payload.download);
          addLog("• session " + payload.session_id);
          break;
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
        case "need_login":
          setNeedLogin(true);
          setStatus("Login required");
          addLog("🔑 " + (payload.message || "Login required"));
          break;
        case "frame":
          setFrame(payload.data);
          break;
        case "login_ok":
          setNeedLogin(false);
          setFrame(null);
          setStatus("Logged in — extracting");
          addLog("✓ " + (payload.message || "Login detected"));
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
        case "ping":
          break; // keepalive, ignore
        default:
          break;
      }
    };

    ws.onclose = () => setRunning(false);
    ws.onerror = () => {
      addLog("⚠ connection lost — backend unreachable or dropped.");
      setStatus("Connection lost");
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
        <header className="mb-8 flex items-center gap-3">
          <img src="/logo.png" alt="LinkPilot" className="h-10 w-10 invert" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Link<span className="text-cyan-400">Pilot</span>
            </h1>
            <p className="text-slate-400">
              Extract external job application links live.
            </p>
          </div>
        </header>

        {/* Controls */}
        <div className="grid gap-4 rounded-2xl bg-slate-900 p-6 shadow-lg md:grid-cols-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Chrome profile</span>
            <input
              className="rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
              value={profile}
              placeholder="enter a profile name"
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
                disabled={!profile.trim()}
                className={
                  "w-full rounded-lg px-4 py-2 font-medium " +
                  (profile.trim()
                    ? "bg-indigo-600 hover:bg-indigo-500"
                    : "cursor-not-allowed bg-slate-700 text-slate-500")
                }
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

        {/* Interactive login panel (CDP screencast) */}
        {needLogin && (
          <div className="mt-6 rounded-2xl border border-amber-500/40 bg-slate-900 p-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-amber-300">
                Log in to Jobright
              </h2>
              <button
                onClick={() => sendInput({ type: "login_done" })}
                className="rounded-lg bg-amber-600 px-3 py-1.5 text-sm font-medium hover:bg-amber-500"
              >
                I'm logged in →
              </button>
            </div>
            <p className="mb-3 text-xs text-slate-400">
              Click and type directly on the page below. When the jobs feed
              appears, extraction starts automatically.
            </p>
            <div className="flex justify-center bg-black/40 p-2">
              {frame ? (
                <img
                  ref={imgRef}
                  src={`data:image/jpeg;base64,${frame}`}
                  onClick={onFrameClick}
                  className="max-w-full cursor-pointer"
                  alt="login"
                />
              ) : (
                <div className="py-20 text-slate-500">Loading page…</div>
              )}
            </div>
          </div>
        )}

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {/* Links table */}
          <div className="rounded-2xl bg-slate-900 p-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">Links ({links.length})</h2>
              <a
                href={downloadUrl || undefined}
                className={
                  "rounded-lg px-3 py-1.5 text-sm font-medium " +
                  (downloadUrl
                    ? "bg-emerald-600 hover:bg-emerald-500"
                    : "pointer-events-none bg-slate-700 text-slate-500")
                }
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
