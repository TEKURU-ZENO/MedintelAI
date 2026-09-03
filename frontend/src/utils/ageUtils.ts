/**
 * ageUtils.ts — Profile type derivation utilities
 *
 * Mirror of the backend profile_service.py logic.
 * Used in: Registration form (live feedback), AuthContext hydration.
 */

export type ProfileType = "early_learner" | "child" | "adult";

/**
 * Calculate age in full years from an ISO date string ("YYYY-MM-DD").
 * Returns null if dob is empty or invalid.
 */
export function calculateAge(dob: string): number | null {
  if (!dob) return null;
  const birth = new Date(dob);
  if (isNaN(birth.getTime())) return null;

  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}

/**
 * Derive profile type from numeric age (mirrors backend age_derived_profile).
 */
export function deriveProfileTypeFromAge(age: number | null): ProfileType {
  if (age === null) return "adult";
  if (age <= 5) return "early_learner";
  if (age <= 15) return "child";
  return "adult";
}

/**
 * Compute effective profile type, respecting preferred_learning_mode override.
 * Used when building local state from /auth/profile response.
 */
export function getEffectiveProfileType(
  dob: string,
  preferredMode?: string | null
): ProfileType {
  const validTypes: ProfileType[] = ["early_learner", "child", "adult"];
  if (preferredMode && validTypes.includes(preferredMode as ProfileType)) {
    return preferredMode as ProfileType;
  }
  const age = calculateAge(dob);
  return deriveProfileTypeFromAge(age);
}

/**
 * Human-readable label for a profile type.
 */
export function profileTypeLabel(pt: ProfileType): string {
  const labels: Record<ProfileType, string> = {
    early_learner: "Early Learner (2–5)",
    child: "Child (6–15)",
    adult: "Adult (16+)",
  };
  return labels[pt] ?? pt;
}
