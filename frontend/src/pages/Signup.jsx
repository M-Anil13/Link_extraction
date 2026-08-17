import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const inputCls =
  "mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500";

export default function Signup() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const post = async (path, body) => {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.json();
  };

  const doSignup = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const d = await post("/auth/signup", { email, password, name });
      if (d.ok) {
        localStorage.setItem("user", JSON.stringify(d));
        navigate("/app");
      } else {
        setError(d.error || "Signup failed");
      }
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="w-full max-w-sm rounded-2xl bg-slate-900 p-8 shadow-lg">
        <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">← Home</Link>
        <h1 className="mt-4 text-2xl font-bold">Create account</h1>

        <form onSubmit={doSignup}>
          <label className="mt-6 block text-sm">
            <span className="text-slate-400">Name</span>
            <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="mt-4 block text-sm">
            <span className="text-slate-400">Email</span>
            <input type="email" className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="mt-4 block text-sm">
            <span className="text-slate-400">Password (min 6)</span>
            <input type="password" className={inputCls} value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}
          <button
            type="submit"
            disabled={busy || !email || password.length < 6}
            className={"mt-6 w-full rounded-lg px-4 py-2 font-medium " +
              (busy || !email || password.length < 6 ? "cursor-not-allowed bg-slate-700 text-slate-500" : "bg-indigo-600 hover:bg-indigo-500")}
          >
            {busy ? "Creating account…" : "Sign up"}
          </button>
          <p className="mt-4 text-center text-sm text-slate-400">
            Have an account? <Link to="/login" className="text-indigo-400 hover:text-indigo-300">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

