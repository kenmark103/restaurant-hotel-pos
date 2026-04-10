import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        host: true,
        port: 5173,
        proxy: {
            '/api': 'http://backend:8000',
            '/socket.io': {
                target: 'http://backend:8000',
                ws: true,
            },
        },
    },
});
