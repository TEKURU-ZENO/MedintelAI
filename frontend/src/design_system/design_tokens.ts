/**
 * design_tokens.ts — Global Design System Tokens
 * 
 * Centralizes colors, spacing, and border radii to ensure visual consistency.
 * Focuses on a warm, elegant, "Pinterest-inspired" but educationally restrained aesthetic.
 */

export const colors = {
  // Base
  background: "#F7F8FA", // Warm off-white/fog gray
  surface: "#FFFFFF",
  surfaceHover: "#F9FAFB",
  
  // Text
  textPrimary: "#111827", // Soft black
  textSecondary: "#6B7280", // Muted gray
  textTertiary: "#9CA3AF", // Light gray
  
  // Accents (Bursts of joy)
  sage: "#86EFAC", // Soft green
  coral: "#FDA4AF", // Soft pink/red
  lavender: "#D8B4FE", // Soft purple
  sunflower: "#FDE047", // Soft yellow
  skyBlue: "#7DD3FC", // Soft blue
  indigo: "#6366F1", // Primary interactive
  indigoLight: "#EEF2FF", // Interactive background
  
  // Semantic
  success: "#10B981", // Green
  warning: "#F59E0B", // Orange
  error: "#EF4444", // Red
};

export const radii = {
  sm: "0.25rem",
  md: "0.5rem",
  lg: "0.75rem",
  xl: "1rem",
  "2xl": "1.5rem",
  "3xl": "2rem",
  pill: "9999px",
  circle: "50%",
};

export const spacing = {
  xs: "0.25rem", // 4px
  sm: "0.5rem",  // 8px
  md: "1rem",    // 16px
  lg: "1.5rem",  // 24px
  xl: "2rem",    // 32px
  "2xl": "3rem", // 48px
  "3xl": "4rem", // 64px
  "4xl": "6rem", // 96px
};
