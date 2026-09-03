/**
 * elevation_tokens.ts — Global Elevation & Shadow System
 * 
 * Soft, diffuse shadows to simulate floating paper and breathable cards.
 */

export const elevation = {
  shadows: {
    // Almost invisible, just grounds the element
    xs: "0 1px 2px rgba(0, 0, 0, 0.02)",
    
    // Default card resting state (soft, long, diffuse)
    sm: "0 4px 20px rgba(0, 0, 0, 0.03)",
    
    // Card hover state (elevated, breathable)
    md: "0 8px 30px rgba(0, 0, 0, 0.06)",
    
    // Popovers, modals, dropdowns
    lg: "0 12px 40px rgba(0, 0, 0, 0.08)",
    
    // Ambient glowing states (for success/celebration)
    glowSage: "0 0 20px rgba(134, 239, 172, 0.4)",
    glowIndigo: "0 0 20px rgba(99, 102, 241, 0.3)",
  },
  
  zIndices: {
    base: 0,
    elevated: 10,
    dropdown: 20,
    sticky: 30,
    modalBase: 40,
    modalContent: 50,
    tooltip: 60,
  }
};
