import { defineConfig } from "vite";
import path from "node:path";

export default defineConfig({
  root: ".",
  publicDir: "public",
  server: {
    // listen on all interfaces so LAN / named hosts can connect
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    // allow access via machine name / alias (Vite 5.1+ host check)
    allowedHosts: [
      "dext-gpu2",
      "dext",
      "localhost",
      ".local",
    ],
    fs: {
      allow: [path.resolve(".."), path.resolve(".")],
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    allowedHosts: [
      "dext-gpu2",
      "dext",
      "localhost",
      ".local",
    ],
  },
});
