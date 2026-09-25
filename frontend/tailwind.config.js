/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0d0f12",
          sunken: "#0a0c0e",
          raised: "#15181c",
          hover: "#1a1e23",
          border: "#262b31",
          strong: "#343a42",
        },
        accent: {
          DEFAULT: "#2dd4a7",
          dim: "#1f9e7d",
          muted: "#16362e",
        },
        ink: {
          DEFAULT: "#e6e9ec",
          muted: "#9aa4ad",
          faint: "#6b747c",
        },
        danger: "#e5484d",
        warn: "#e5a33d",
        info: "#6ea8d8",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["10.5px", { lineHeight: "14px" }],
      },
      boxShadow: {
        card: "inset 0 1px 0 0 rgba(255,255,255,0.03), 0 1px 2px 0 rgba(0,0,0,0.35)",
        raised: "inset 0 1px 0 0 rgba(255,255,255,0.04), 0 8px 24px -12px rgba(0,0,0,0.6)",
      },
      transitionTimingFunction: {
        "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
      },
      keyframes: {
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
        // Time until the next scheduled refresh (duration set inline).
        countdown: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both",
        "fade-in": "fade-in 0.8s ease-out both",
        shimmer: "shimmer 1.6s ease-in-out infinite",
        indeterminate: "indeterminate 1.2s cubic-bezier(0.65, 0, 0.35, 1) infinite",
        "soft-pulse": "soft-pulse 1.6s ease-in-out infinite",
        countdown: "countdown linear both",
      },
    },
  },
  plugins: [],
};
