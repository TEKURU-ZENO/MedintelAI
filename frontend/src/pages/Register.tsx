import { useState } from "react";
import { api } from "../api/client";
import { useNavigate, Link } from "react-router-dom";
import { calculateAge, deriveProfileTypeFromAge, profileTypeLabel } from "../utils/ageUtils";

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [parentId, setParentId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  // Live-derive profile type from DOB input for visual feedback
  const age = calculateAge(dateOfBirth);
  const derivedProfile = deriveProfileTypeFromAge(age);
  const isMinor = age !== null && age <= 15;
  const showParentField = isMinor;

  // Maximum DOB = today (can't be born in the future)
  const today = new Date().toISOString().split("T")[0];

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/register", {
        email,
        password,
        full_name: fullName,
        date_of_birth: dateOfBirth,
        parent_id: parentId ? parseInt(parentId) : null,
      });
      nav("/login", { state: { registered: true } });
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed. Please try again.");
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
          <p className="text-textSecondary mt-1 font-medium text-sm">Create your learning profile</p>
        </div>

        <form
          onSubmit={submit}
          className="bg-surface border border-border rounded-3xl shadow-sm hover:shadow-md p-8 space-y-5 transition-all duration-300"
        >
          {error && (
            <div className="bg-danger/10 border border-danger/25 text-danger text-xs sm:text-sm font-semibold rounded-2xl px-4 py-3">
              {error}
            </div>
          )}

          {/* Full Name */}
          <div>
            <label className="block text-xs font-bold text-textSecondary mb-1.5 uppercase tracking-wider">
              Full Name
            </label>
            <input
              id="reg-full-name"
              type="text"
              required
              placeholder="e.g. Arjun Kumar"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-textPrimary focus:outline-none focus:ring-2 focus:ring-indigo/40 transition-colors"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-xs font-bold text-textSecondary mb-1.5 uppercase tracking-wider">
              Email
            </label>
            <input
              id="reg-email"
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
              id="reg-password"
              type="password"
              required
              minLength={6}
              placeholder="At least 6 characters"
              className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-textPrimary focus:outline-none focus:ring-2 focus:ring-indigo/40 transition-colors"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {/* Date of Birth */}
          <div>
            <label className="block text-xs font-bold text-textSecondary mb-1.5 uppercase tracking-wider">
              Date of Birth
            </label>
            <input
              id="reg-dob"
              type="date"
              required
              max={today}
              className="w-full bg-surface border border-border rounded-xl px-4 py-2.5 text-textPrimary focus:outline-none focus:ring-2 focus:ring-indigo/40 transition-colors"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
            />

            {/* Live profile type preview */}
            {dateOfBirth && age !== null && (
              <div className="mt-2.5 flex items-center gap-2">
                <span className="text-xs text-textTertiary font-medium">Learning profile:</span>
                <span
                  className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                    derivedProfile === "early_learner"
                      ? "bg-pink-100 dark:bg-pink-950/40 text-pink-700 dark:text-pink-300"
                      : derivedProfile === "child"
                      ? "bg-indigoLight text-indigo"
                      : "bg-green-100 dark:bg-green-950/40 text-green-700 dark:text-green-300"
                  }`}
                >
                  {profileTypeLabel(derivedProfile)}
                </span>
              </div>
            )}
          </div>

          {/* Parent linking — shown only for minors without parent_id */}
          {showParentField && (
            <div className="bg-amber-500/10 border border-amber-500/25 rounded-2xl p-4 space-y-2">
              <p className="text-xs font-bold text-amber-600 dark:text-amber-400">
                👋 Looks like you're registering a young learner!
              </p>
              <p className="text-[11px] text-textSecondary font-medium leading-normal">
                You can optionally link a parent account now, or do it later from
                the dashboard. This enables parental progress reports.
              </p>
              <div>
                <label className="block text-[10px] font-bold text-textSecondary mb-1 uppercase tracking-wider">
                  Parent Account ID (optional)
                </label>
                <input
                  id="reg-parent-id"
                  type="number"
                  placeholder="Leave blank to link later"
                  className="w-full border border-border bg-surface rounded-xl px-3 py-2 text-sm text-textPrimary focus:outline-none focus:ring-2 focus:ring-indigo/40 transition-colors"
                  value={parentId}
                  onChange={(e) => setParentId(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Submit */}
          <button
            id="reg-submit"
            type="submit"
            disabled={loading}
            className="w-full bg-indigo hover:bg-indigoHover disabled:bg-indigo/50 text-white font-bold py-3.5 rounded-xl transition-colors shadow-sm cursor-pointer"
          >
            {loading ? "Creating account…" : "Create Account"}
          </button>

          <div className="text-center text-xs sm:text-sm text-textTertiary font-medium">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-indigo font-bold hover:underline"
            >
              Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
