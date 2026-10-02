import { defineConfig } from "vitest/config";
import path from "path";
import { createRequire } from "module";

const templateRoot = path.resolve(import.meta.dirname);
// vite.config.ts'teki define burada geçerli DEĞİLDİR; Sidebar gibi
// __APP_VERSION__ kullanan bir bileşeni test eden dosya eklenirse
// bu olmadan ReferenceError alınır.
const pkg = createRequire(import.meta.url)("./package.json") as { version: string };

export default defineConfig({
  root: templateRoot,
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  resolve: {
    alias: {
      "@": path.resolve(templateRoot, "src"),
      "@contracts": path.resolve(templateRoot, "contracts"),
      // vite.config.ts ile aynı: yoksa api/queries/connection.ts testte yüklenemez.
      "@db": path.resolve(templateRoot, "db"),
      db: path.resolve(templateRoot, "db"),
      "@assets": path.resolve(templateRoot, "attached_assets"),
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts", "api/**/*.test.ts", "api/**/*.spec.ts", "src/**/*.test.ts"],
    setupFiles: ["./tests/setup.ts"],
    globals: true,
  },
});
