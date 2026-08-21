/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#090d16",
        surface: "#111827",
        "surface-border": "#1f293d",
        primary: "#3b82f6",
        "primary-hover": "#2563eb",
        accent: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
        muted: "#94a3b8",
      },
    },
  },
  plugins: [],
}
