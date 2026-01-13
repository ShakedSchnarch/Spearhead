import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/spearhead/',
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('recharts')) return 'vendor-recharts';
            if (id.includes('@mantine')) return 'vendor-mantine';
            if (id.includes('chart.js')) return 'vendor-chartjs';
            return 'vendor';
          }
        },
      },
    },
  },
});
