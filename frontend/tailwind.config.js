/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          extreme: "#ef4444",
          high: "#f97316",
          medium: "#eab308",
          low: "#22c55e",
          minimal: "#06b6d4",
        },
      },
    },
  },
  plugins: [],
};
