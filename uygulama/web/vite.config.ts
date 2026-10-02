import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// Geliştirmede /api istekleri arka uca (127.0.0.1:8810) aktarılır; üretimde ön yüz
// derlenip arka uç tarafından aynı kökenden sunulur (tek süreç, tek port — ADR-003).
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8810" },
  },
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  build: { outDir: "dist", emptyOutDir: true },
})
