import { GoogleLogin } from "@react-oauth/google";
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Login() {
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const onSuccess = async (cred) => {
    setError("");
    try {
      const res = await fetch(`${API}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: cred.credential }),
      });
      const data = await res.json();
      if (data.ok) {
        localStorage.setItem("user", JSON.stringify(data));
        navigate("/app");
      } else {
        setError(data.error || "Login failed");
      }
    } catch (e) {
      setError("Could not reach the server.");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="w-full max-w-sm rounded-2xl bg-slate-900 p-8 text-center shadow-lg">
        <Link to="/" className="text-sm text-slate-400 hover:text-slate-200">
          ← Home
        </Link>
        <h1 className="mt-4 text-2xl font-bold">Sign in</h1>
        <p className="mt-2 text-sm text-slate-400">
          Use your Google account to access the extractor.
        </p>

        <div className="mt-8 flex justify-center">
          <GoogleLogin
            onSuccess={onSuccess}
            onError={() => setError("Google sign-in failed")}
          />
        </div>

        {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}
      </div>
    </div>
  );
}
