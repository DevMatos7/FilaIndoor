/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f7f4",
          100: "#dceee6",
          500: "#1f6b4a",
          700: "#154a34",
          900: "#0c2b1e",
        },
        ink: "#14201a",
        sand: "#f3f6f4",
      },
      fontFamily: {
        display: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"DM Sans"', "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
