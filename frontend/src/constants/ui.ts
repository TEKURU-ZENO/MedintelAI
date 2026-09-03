/**
 * UI & Canvas Configuration Constants
 */

export interface Dimension {
  width: number;
  height: number;
}

export const CANVAS_SIZES = {
  alphabet: {
    desktop:     { width: 500, height: 500 },
    tablet:      { width: 420, height: 420 },
    smallTablet: { width: 350, height: 350 },
    mobile:      { width: 280, height: 280 },
  },
  word: {
    desktop:     { width: 500, height: 500 },
    tablet:      { width: 420, height: 420 },
    smallTablet: { width: 350, height: 350 },
    mobile:      { width: 280, height: 280 },
  },
  freeDraw: {
    desktop:     { width: 600, height: 500 },
    tablet:      { width: 480, height: 400 },
    smallTablet: { width: 380, height: 320 },
    mobile:      { width: 300, height: 260 },
  },
};

/**
 * Get responsive canvas size based on window width
 */
export function getResponsiveCanvasSize(
  moduleType: string,
  windowWidth: number
): Dimension {
  const isDesktop = windowWidth >= 1024;
  const isTablet = windowWidth >= 768 && windowWidth < 1024;
  const isSmallTablet = windowWidth >= 480 && windowWidth < 768;

  const key =
    moduleType === "alphabet_practice" ? "alphabet"
    : moduleType === "word_practice" ? "word"
    : "freeDraw";

  const config = CANVAS_SIZES[key as keyof typeof CANVAS_SIZES] || CANVAS_SIZES.alphabet;
  
  if (isDesktop) return config.desktop;
  if (isTablet) return config.tablet;
  if (isSmallTablet) return config.smallTablet;
  return config.mobile;
}
