/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // Warm charcoal + champagne (adapted from the Maison Solenne direction).
      // Status colours are deliberately NOT the brand gold: sage = good,
      // ochre = warning, rose = failing, so health never reads as branding.
      colors: {
        surface: {
          DEFAULT: "#161413",
          sunken: "#100f0e",
          raised: "#1e1c1a",
          hover: "#23211f",
          border: "#39342d",
          strong: "#4d463d",
        },
        accent: {
          DEFAULT: "#cdb284",
          dim: "#a88f63",
          muted: "#3a3226",
        },
        ink: {
          DEFAULT: "#ede8de",
          muted: "#9f958a",
          faint: "#797167",
        },
        ivory: "#f5f0e7",
        positive: "#89b39b",
        danger: "#cf5959",
        warn: "#d48354",
        info: "#879eb5",
      },
      fontFamily: {
        sans: ["Jost", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Italiana", "ui-serif", "Georgia", "serif"],
        serif: ["Cormorant", "ui-serif", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "2px",
        md: "3px",
        lg: "4px",
        xl: "6px",
      },
      fontSize: {
        "2xs": ["10.5px", { lineHeight: "14px" }],
      },
      boxShadow: {
        card: "inset 0 1px 0 0 rgba(237,232,222,0.025), 0 1px 2px 0 rgba(0,0,0,0.35)",
        raised: "inset 0 1px 0 0 rgba(255,255,255,0.04), 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      transitionTimingFunction: {
        "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
      },
      keyframes: {
        "light-leak": {
          "0%": { transform: "translate(-15%, -10%)" },
          "100%": { transform: "translate(55%, 25%)" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        indeterminate: {
          "0%": { transform: "translateX(-100%) scaleX(0.4)" },
          "100%": { transform: "translateX(250%) scaleX(0.4)" },
        },
        "soft-pulse": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.45", transform: "scale(0.85)" },
        },
      },
      animation: {
        "light-leak": "light-leak 20s ease-in-out infinite alternate",
        "fade-in-up": "fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both",
        "fade-in": "fade-in 0.8s ease-out both",
        shimmer: "shimmer 1.6s ease-in-out infinite",
        indeterminate: "indeterminate 1.2s cubic-bezier(0.65, 0, 0.35, 1) infinite",
        "soft-pulse": "soft-pulse 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
