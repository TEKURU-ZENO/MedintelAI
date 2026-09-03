import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#F0F2F5", // Pinterest gray
        surface: "#FFFFFF",
        surfaceHover: "#F9FAFB",
        sage: "#86EFAC",
        coral: "#FDA4AF",
        lavender: "#D8B4FE",
        sunflower: "#FDE047",
        skyBlue: "#7DD3FC",
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        display: ['"Outfit"', '"Nunito"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        // Soft, diffuse elevation tokens
        xs: "0 1px 2px rgba(0, 0, 0, 0.02)",
        sm: "0 4px 20px rgba(0, 0, 0, 0.03)",
        md: "0 8px 30px rgba(0, 0, 0, 0.06)",
        lg: "0 12px 40px rgba(0, 0, 0, 0.08)",
        glowSage: "0 0 20px rgba(134, 239, 172, 0.4)",
        glowIndigo: "0 0 20px rgba(99, 102, 241, 0.3)",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      transitionDuration: {
        '250': '250ms',
        '400': '400ms',
      }
    },
  },
  plugins: [],
} satisfies Config;
