/**
 * motion_tokens.ts — Global Motion & Animation Hierarchy
 * 
 * Defines the emotional pacing of the application.
 */

export const motion = {
  // Durations
  durations: {
    tiny: "150ms",     // Micro-interactions, tiny feedback
    hover: "250ms",    // Card hovers, soft button states
    standard: "300ms", // Page transitions, standard modals
    slow: "500ms",     // Ambient loops, slow reveals
    spring: "700ms",   // Success celebrations, bouncy states
  },
  
  // Easings
  easings: {
    standard: "cubic-bezier(0.4, 0, 0.2, 1)", // ease-out
    spring: "cubic-bezier(0.34, 1.56, 0.64, 1)", // Bouncy, playful
    linear: "linear",
    inOut: "cubic-bezier(0.4, 0, 0.2, 1)",
  },

  // Tailwind Class Combinations
  classes: {
    hover: "transition-all duration-250 ease-out",
    spring: "transition-all duration-700 cubic-bezier(0.34, 1.56, 0.64, 1)",
    fade: "transition-opacity duration-300 ease-out",
  }
};
