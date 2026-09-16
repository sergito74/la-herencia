import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F8F9F6",
        surface: { DEFAULT: "#FFFFFF", sunken: "#F1F0EA" },
        border: { DEFAULT: "#E3E0D6", strong: "#C9C4B4" },
        ink: { primary: "#2B2A25", secondary: "#6B6858", muted: "#9C977F" },
        agro: { DEFAULT: "#2F5233", light: "#E7EEE3" },
        livestock: { DEFAULT: "#8A5A2B", light: "#F3E7D8" },
        finance: { DEFAULT: "#3E5C76", light: "#E6EBF0" },
        status: {
          success: "#3F7D45",
          "success-bg": "#E4F0E5",
          warning: "#B5792A",
          "warning-bg": "#FBEEDC",
          danger: "#B23A2E",
          "danger-bg": "#F7E3E0",
          neutral: "#6B6858",
          "neutral-bg": "#EDEBE3",
        },
      },
      fontFamily: { sans: ["var(--font-inter)", "system-ui", "sans-serif"] },
      borderRadius: { sm: "4px", md: "8px", lg: "12px" },
    },
  },
  plugins: [],
};

export default config;
