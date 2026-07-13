import { defineConfig } from "vite";
import path from "path";
import fs from "fs";

const rawPort = process.env.PORT;
if (!rawPort) throw new Error("PORT environment variable is required but was not provided.");
const port = Number(rawPort);
if (Number.isNaN(port) || port <= 0) throw new Error(`Invalid PORT value: "${rawPort}"`);

const basePath = process.env.BASE_PATH || "/";

function findHtmlFiles(dir: string, base: string, results: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const rel = path.relative(base, full);
    if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== "dist") {
      findHtmlFiles(full, base, results);
    } else if (entry.isFile() && entry.name.endsWith(".html")) {
      results.push(rel);
    }
  }
  return results;
}

const root = path.resolve(import.meta.dirname);
const htmlFiles = findHtmlFiles(root, root);

const input: Record<string, string> = {};
for (const file of htmlFiles) {
  const name = file.replace(/\.html$/, "").replace(/[\\/]/g, "_") || "index";
  input[name] = path.resolve(root, file);
}

export default defineConfig({
  base: basePath,
  root,
  build: {
    outDir: path.resolve(root, "dist/public"),
    emptyOutDir: true,
    rollupOptions: { input },
  },
  server: {
    port,
    strictPort: true,
    host: "0.0.0.0",
    allowedHosts: true,
  },
  preview: {
    port,
    host: "0.0.0.0",
    allowedHosts: true,
  },
});
