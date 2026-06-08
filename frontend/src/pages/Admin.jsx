import { useState } from "react";
import { Link } from "react-router-dom";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Admin() {
  const [key, setKey] = useState(localStorage.getItem("adminKey") || "");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setError("");
    setBusy(true);
    try {
      const res = await fetch(`${API}/admin/users`, {
        headers: { "X-Admin-Key": key },
      });
      const d = await res.json();
      if (d.ok) {
        localStorage.setItem("adminKey", key);
        setData(d);
      } else {
        setError(d.error || "Unauthorized");
        setData(null);
      }
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center rounded-xl bg-slate-950 p-2 ring-1 ring-cyan-500/30">
              <img src="/logo.png" alt="LinkPilot" className="h-7 w-7 invert" />
            </span>
            <h1 className="text-3xl font-bold">Admin dashboard</h1>
          </div>
          <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">
            ← Home
          </Link>
        </div>

        {/* Key entry */}
        <div className="flex gap-2">
          <input
            type="password"
            placeholder="Admin key"
            className="flex-1 rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <button
            onClick={load}
            disabled={busy || !key}
            className="rounded-lg bg-indigo-600 px-5 py-2 font-medium hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500"
          >
            {busy ? "Loading…" : "Load"}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}

        {data && (
          <>
            {/* Totals */}
            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              {[
                ["Users", data.total_users],
                ["Total runs", data.total_runs],
                ["Total links", data.total_links],
              ].map(([label, val]) => (
                <div key={label} className="rounded-2xl bg-slate-900 p-6">
                  <p className="text-sm text-slate-400">{label}</p>
                  <p className="mt-1 text-3xl font-bold text-indigo-400">{val}</p>
                </div>
              ))}
            </div>

            {/* Users table */}
            <div className="mt-8 overflow-auto rounded-2xl bg-slate-900 p-6">
              <table className="w-full text-left text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="py-2 pr-4">User</th>
                    <th className="py-2 pr-4">Logins</th>
                    <th className="py-2 pr-4">Runs</th>
                    <th className="py-2 pr-4">First seen</th>
                    <th className="py-2">Last seen</th>
                  </tr>
                </thead>
                <tbody>
                  {data.users.map((u) => (
                    <tr key={u.email} className="border-t border-slate-800">
                      <td className="py-2 pr-4">{u.name || u.email}</td>
                      <td className="py-2 pr-4">{u.login_count}</td>
                      <td className="py-2 pr-4">{u.run_count}</td>
                      <td className="py-2 pr-4 text-slate-500">
                        {u.first_seen?.slice(0, 16).replace("T", " ")}
                      </td>
                      <td className="py-2 text-slate-500">
                        {u.last_seen?.slice(0, 16).replace("T", " ")}
                      </td>
                    </tr>
                  ))}
                  {data.users.length === 0 && (
                    <tr>
                      <td colSpan="5" className="py-6 text-center text-slate-500">
                        No users yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
