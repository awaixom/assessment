import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://localhost:8000",
      "/worklogs": "http://localhost:8000",
      "/generate-remittances": "http://localhost:8000",
      "/preview-settlement": "http://localhost:8000",
    },
  },
});
