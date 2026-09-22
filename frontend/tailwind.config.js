/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0d0f12",
          raised: "#15181c",
          border: "#262b31",
        },
        accent: {
          DEFAULT: "#2dd4a7",
          dim: "#1f9e7d",
        },
        ink: {
          DEFAULT: "#e6e9ec",
          muted: "#9aa4ad",
          faint: "#6b747c",
        },
        danger: "#e5484d",
        warn: "#e5a33d",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
