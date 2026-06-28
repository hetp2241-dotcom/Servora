import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    var backend = env.VITE_DJANGO_ORIGIN || "http://127.0.0.1:8000";
    return {
        plugins: [react(), tailwindcss()],
        resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
        server: {
            port: 5173,
            proxy: {
                "/api": { target: backend, changeOrigin: true },
                "/media": { target: backend, changeOrigin: true },
                "/static": { target: backend, changeOrigin: true },
                "/ws": { target: backend, ws: true, changeOrigin: true }
            }
        },
        build: { sourcemap: true, chunkSizeWarningLimit: 800 }
    };
});
