import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (data.ok) {
        localStorage.setItem("user", JSON.stringify(data));
        navigate("/app");
      } else {
        setError(data.error || "Login failed");
      }
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-2xl bg-slate-900 p-8 shadow-lg"
      >
        <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">
          ← Home
        </Link>
        <div className="mt-4 flex items-center gap-2">
          <span className="flex items-center justify-center rounded-xl bg-white p-2 shadow-lg shadow-cyan-500/20">
            <img src="/logo.png" alt="LinkPilot" className="h-7 w-7" />
          </span>
          <h1 className="text-2xl font-bold">Sign in</h1>
        </div>
        <p className="mt-2 text-sm text-slate-400">Log in to use the extractor.</p>

        <label className="mt-6 block text-sm">
          <span className="text-slate-400">Username</span>
          <input
            className="mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
        </label>

        <label className="mt-4 block text-sm">
          <span className="text-slate-400">Password</span>
          <input
            type="password"
            className="mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}

        <button
          type="submit"
          disabled={busy || !username || !password}
          className={
            "mt-6 w-full rounded-lg px-4 py-2 font-medium " +
            (busy || !username || !password
              ? "cursor-not-allowed bg-slate-700 text-slate-500"
              : "bg-indigo-600 hover:bg-indigo-500")
          }
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
