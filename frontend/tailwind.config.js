/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f6f2ea",
        "paper-deep": "#efe9dd",
        surface: "#ffffff",
        "surface-2": "#fbf8f2",
        border: "#e3dccd",
        "border-strong": "#cdc4b0",
        ink: "#1c1a16",
        "ink-2": "#3a3730",
        muted: "#756f60",
        "muted-2": "#98917f",
      },
      fontFamily: {
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
