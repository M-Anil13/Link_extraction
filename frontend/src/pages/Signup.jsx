import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const inputCls =
  "mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500";

export default function Signup() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1 = details, 2 = OTP
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
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

  const doSignup = async (e) => {
    e.preventDefault();
    setError(""); setInfo(""); setBusy(true);
    try {
      const d = await post("/auth/signup", { email, password, name });
      if (d.ok) {
        setInfo("Code sent to your email.");
        setStep(2);
      } else setError(d.error || "Signup failed");
    } catch {
      setError("Could not reach the server.");
    } finally { setBusy(false); }
  };

  const doVerify = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const d = await post("/auth/verify", { email, otp });
      if (d.ok) {
        localStorage.setItem("user", JSON.stringify(d));
        navigate("/app");
      } else setError(d.error || "Verification failed");
    } catch {
      setError("Could not reach the server.");
    } finally { setBusy(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="w-full max-w-sm rounded-2xl bg-slate-900 p-8 shadow-lg">
        <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">← Home</Link>
        <h1 className="mt-4 text-2xl font-bold">
          {step === 1 ? "Create account" : "Verify email"}
        </h1>

        {step === 1 ? (
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
              {busy ? "Sending…" : "Sign up"}
            </button>
            <p className="mt-4 text-center text-sm text-slate-400">
              Have an account? <Link to="/login" className="text-indigo-400 hover:text-indigo-300">Sign in</Link>
            </p>
          </form>
        ) : (
          <form onSubmit={doVerify}>
            <p className="mt-2 text-sm text-slate-400">Enter the 6-digit code sent to {email}.</p>
            <label className="mt-6 block text-sm">
              <span className="text-slate-400">Verification code</span>
              <input className={inputCls} value={otp} onChange={(e) => setOtp(e.target.value)} maxLength={6} autoFocus />
            </label>
            {info && <p className="mt-3 text-sm text-emerald-400">{info}</p>}
            {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
            <button
              type="submit"
              disabled={busy || otp.length < 6}
              className={"mt-6 w-full rounded-lg px-4 py-2 font-medium " +
                (busy || otp.length < 6 ? "cursor-not-allowed bg-slate-700 text-slate-500" : "bg-indigo-600 hover:bg-indigo-500")}
            >
              {busy ? "Verifying…" : "Verify & continue"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
