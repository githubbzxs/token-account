import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  root: 'frontend',
  publicDir: 'public',
  build: {
    outDir: '../src/token_account/static',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined;
          }

          if (id.includes('/echarts/') || id.includes('/zrender/')) {
            return 'echarts';
          }

          if (id.includes('@mantine/charts') || id.includes('/recharts/')) {
            return 'charts';
          }

          if (
            id.includes('@mantine/core') ||
            id.includes('@mantine/hooks') ||
            id.includes('@mantine/dates') ||
            id.includes('/dayjs/')
          ) {
            return 'mantine';
          }

          return undefined;
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
});
