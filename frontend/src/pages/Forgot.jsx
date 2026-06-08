import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const inputCls =
  "mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500";

export default function Forgot() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1 = request, 2 = reset
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  const post = async (path, body) => {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.json();
  };

  const doRequest = async (e) => {
    e.preventDefault();
    setError(""); setInfo(""); setBusy(true);
    try {
      const d = await post("/auth/forgot", { email });
      if (d.ok) { setInfo("If that email exists, a code was sent."); setStep(2); }
      else setError(d.error || "Request failed");
    } catch { setError("Could not reach the server."); }
    finally { setBusy(false); }
  };

  const doReset = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const d = await post("/auth/reset", { email, otp, new_password: newPassword });
      if (d.ok) navigate("/login");
      else setError(d.error || "Reset failed");
    } catch { setError("Could not reach the server."); }
    finally { setBusy(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="w-full max-w-sm rounded-2xl bg-slate-900 p-8 shadow-lg">
        <Link to="/login" className="text-sm text-slate-400 hover:text-slate-200">← Back to sign in</Link>
        <h1 className="mt-4 text-2xl font-bold">Reset password</h1>

        {step === 1 ? (
          <form onSubmit={doRequest}>
            <label className="mt-6 block text-sm">
              <span className="text-slate-400">Email</span>
              <input type="email" className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
            </label>
            {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}
            <button type="submit" disabled={busy || !email}
              className={"mt-6 w-full rounded-lg px-4 py-2 font-medium " +
                (busy || !email ? "cursor-not-allowed bg-slate-700 text-slate-500" : "bg-indigo-600 hover:bg-indigo-500")}>
              {busy ? "Sending…" : "Send reset code"}
            </button>
          </form>
        ) : (
          <form onSubmit={doReset}>
            <label className="mt-6 block text-sm">
              <span className="text-slate-400">Reset code</span>
              <input className={inputCls} value={otp} onChange={(e) => setOtp(e.target.value)} maxLength={6} autoFocus />
            </label>
            <label className="mt-4 block text-sm">
              <span className="text-slate-400">New password (min 6)</span>
              <input type="password" className={inputCls} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </label>
            {info && <p className="mt-3 text-sm text-emerald-400">{info}</p>}
            {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
            <button type="submit" disabled={busy || otp.length < 6 || newPassword.length < 6}
              className={"mt-6 w-full rounded-lg px-4 py-2 font-medium " +
                (busy || otp.length < 6 || newPassword.length < 6 ? "cursor-not-allowed bg-slate-700 text-slate-500" : "bg-indigo-600 hover:bg-indigo-500")}>
              {busy ? "Updating…" : "Set new password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
