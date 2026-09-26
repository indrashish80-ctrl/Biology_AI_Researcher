import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    host: "0.0.0.0",
    hmr: false,
    // Standalone `vite` dev mode: proxy API calls to the FastAPI server
    // (scripts/dev.sh / api/server.py). The PORT env var matches the server's.
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${process.env.PORT ?? 8000}`,
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
