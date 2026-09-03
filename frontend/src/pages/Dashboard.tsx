/**
 * Dashboard.tsx — V2 Adaptive Shell Router
 *
 * This is the single entry point after login.
 * It reads profileType from AuthContext and renders the correct shell.
 * No logic lives here — it is a pure routing/loading layer.
 *
 * Shell components:
 *   EarlyLearnerShell → ages 2-5 (cartoon, gamified)
 *   ChildShell        → ages 6-15 (motivational, XP-driven)
 *   AdultShell        → ages 16+ (clean, professional)
 */
import { useAuth } from "../auth/AuthContext";
import EarlyLearnerShell from "../components/shells/EarlyLearnerShell";
import ChildShell from "../components/shells/ChildShell";
import AdultShell from "../components/shells/AdultShell";

export default function Dashboard() {
  const { profileType, isLoading, user } = useAuth();

  // Loading state — shown while /auth/profile is being fetched
  if (isLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-3">
          <div className="text-4xl animate-pulse">✍️</div>
          <p className="text-gray-500 text-sm font-medium">
            Loading your learning profile…
          </p>
        </div>
      </div>
    );
  }

  // Route to correct adaptive shell
  if (profileType === "early_learner") return <EarlyLearnerShell />;
  if (profileType === "child") return <ChildShell />;
  return <AdultShell />;
}
