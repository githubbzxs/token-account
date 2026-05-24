import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: "web",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/data.json": "http://127.0.0.1:8000",
      "/legacy-report.css": "http://127.0.0.1:8000",
      "/legacy-report-runtime.js": "http://127.0.0.1:8000"
    },
  },
});
