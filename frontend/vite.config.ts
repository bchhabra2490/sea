import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: `${root}/index.html`,
        bot: `${root}/bot.html`,
        integrate: `${root}/bot-docs.html`,
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/analyze": "http://127.0.0.1:8000",
      "/pipeline": "http://127.0.0.1:8000",
      "/bot": "http://127.0.0.1:8000",
      "/insights": "http://127.0.0.1:8000",
      "/topics": "http://127.0.0.1:8000",
      "/clusters": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
