import path from "path"
const __dirname = import.meta.dirname
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { createRequire } from "module"

// Sürüm TEK KAYNAKTAN gelir: package.json. Arayüzde elle yazılan sürüm
// dizgesi zamanla package.json'dan ayrışıyordu (UI "v3.0" derken paket
// "0.0.0" idi); enjekte edilince ayrışması yapısal olarak imkânsız.
const pkg = createRequire(import.meta.url)("./package.json") as { version: string }

// https://vite.dev/config/
// Sınama (A6): Atölye aynı FastAPI sürecinden /atolye/ altında sunulur (tek süreç,
// tek port — ADR-004). Geliştirmede /api istekleri arka uca (127.0.0.1:8810) aktarılır;
// Hono dev sunucusu ve Kimi denetim eklentisi kaldırıldı.
export default defineConfig({
  base: "/atolye/",
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 3000,
    fs: { strict: false },
    proxy: { "/api": "http://127.0.0.1:8810" },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@contracts": path.resolve(__dirname, "./contracts"),
      "@db": path.resolve(__dirname, "./db"),
      "db": path.resolve(__dirname, "./db"),
    },
  },
  envDir: path.resolve(__dirname),
  build: {
    outDir: path.resolve(__dirname, "dist"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Split heavy vendor deps into separate cacheable chunks instead of
        // one ~1.2 MB bundle.
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("recharts") || id.includes("/d3-") || id.includes("victory-vendor"))
            return "charts";
          if (id.includes("@xyflow") || id.includes("/d3-zoom") || id.includes("/d3-drag"))
            return "flow";
          if (id.includes("@radix-ui") || id.includes("cmdk") || id.includes("vaul"))
            return "ui";
          if (id.includes("@trpc") || id.includes("@tanstack") || id.includes("superjson"))
            return "data";
          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("/react-router/") ||
            id.includes("/scheduler/")
          )
            return "react";
          return "vendor";
        },
      },
    },
  },
});
