import { useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useNavigate, Link, useLocation } from "react-router-dom";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const nav = useNavigate();

  // Show success banner if redirected from /register
  const location = useLocation();
  const justRegistered = (location.state as any)?.registered === true;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // FastAPI OAuth2PasswordRequestForm requires URL-encoded form data
      const form = new URLSearchParams();
      form.append("username", email);
      form.append("password", password);

      const res = await api.post("/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      // login() stores the token and triggers /auth/profile hydration
      await login(res.data.access_token);
      nav("/dashboard");
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Login failed. Check your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 transition-colors duration-300">
      <div className="w-full max-w-md">
        
        {/* Header */}
        <div className="text-center mb-8 cursor-pointer" onClick={() => nav("/")}>
          <div className="w-12 h-12 bg-indigo rounded-full flex items-center justify-center text-white font-bold text-xl shadow-glow-indigo mx-auto mb-3">
            A
          </div>
          <h1 className="font-display font-bold text-textPrimary text-3xl tracking-tight">Aksharabyasa</h1>
          <p className="text-textSecondary mt-1 font-medium text-sm">Adaptive Handwriting Platform</p>
        </div>

        <form
          onSubmit={submit}
          className="bg-surface border border-border rounded-3xl shadow-sm hover:shadow-md p-8 space-y-5 transition-all duration-300"
        >
          {/* Post-registration success banner */}
          {justRegistered && (
            <div className="bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 text-xs sm:text-sm font-semibold rounded-2xl px-4 py-3 flex items-center gap-2">
              <span>🎉</span>
              <span>Account created! Sign in to start learning.</span>
            </div>
          )}

          {error && (
            <div className="bg-danger/10 border border-danger/25 text-danger text-xs sm:text-sm font-semibold rounded-2xl px-4 py-3">
              {error}
            </div>
          )}

          {/* Email */}
          <div>
            <label className="block text-xs font-bold text-textSecondary mb-1.5 uppercase tracking-wider">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              placeholder="you@example.com"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-textPrimary focus:outline-none focus:ring-2 focus:ring-indigo/40 transition-colors"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-bold text-textSecondary mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              required
              placeholder="Your password"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-textPrimary focus:outline-none focus:ring-2 focus:ring-indigo/40 transition-colors"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {/* Submit */}
          <button
            id="login-submit"
            type="submit"
            disabled={loading}
            className="w-full bg-indigo hover:bg-indigoHover disabled:bg-indigo/50 text-white font-bold py-3.5 rounded-xl transition-colors shadow-sm cursor-pointer"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>

          <div className="text-center text-xs sm:text-sm text-textTertiary font-medium">
            Don't have an account?{" "}
            <Link
              to="/register"
              className="text-indigo font-bold hover:underline"
            >
              Create one
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
