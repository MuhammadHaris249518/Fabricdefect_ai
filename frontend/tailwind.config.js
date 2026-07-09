/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#1F3A63",
        accent: "#2A6FDB",
        success: "#1F9D6B",
        alert: "#D64545",
        warning: "#E0A32E",
        surface: "#F4F6FB",
        "text-primary": "#1C2333",
        "text-secondary": "#667085",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Consolas", "monospace"],
      },
      borderRadius: {
        card: "8px",
      },
    },
  },
  plugins: [],
};