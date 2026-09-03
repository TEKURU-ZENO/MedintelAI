/**
 * typography.ts — Global Typography System
 * 
 * Clean, round, and legible for young learners and elegant for parents.
 */

export const typography = {
  fonts: {
    sans: "'Inter', system-ui, -apple-system, sans-serif",
    display: "'Outfit', 'Nunito', system-ui, sans-serif", // Rounded, friendly
    mono: "'Fira Code', ui-monospace, SFMono-Regular, monospace",
  },
  
  weights: {
    regular: "400",
    medium: "500",
    semibold: "600",
    bold: "700",
    black: "900", // For target words / big tracing letters
  },
  
  sizes: {
    xs: "0.75rem",   // 12px
    sm: "0.875rem",  // 14px
    base: "1rem",    // 16px
    lg: "1.125rem",  // 18px
    xl: "1.25rem",   // 20px
    "2xl": "1.5rem", // 24px
    "3xl": "1.875rem",// 30px
    "4xl": "2.25rem", // 36px
    "5xl": "3rem",    // 48px
    "6xl": "3.75rem", // 60px
    "huge": "8rem",   // Practice canvas single letters
  },
  
  lineHeights: {
    tight: "1.2",
    snug: "1.375",
    normal: "1.5",
    relaxed: "1.625",
  }
};
