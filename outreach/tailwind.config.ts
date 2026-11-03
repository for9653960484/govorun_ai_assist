import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1c1917",
        paper: "#f4f1ea",
        pine: "#1f4b3a",
      },
    },
  },
  plugins: [],
};

export default config;
