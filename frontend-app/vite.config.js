import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/spearhead/',
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined;
          }
          if (id.includes('@mantine') || id.includes('@emotion') || id.includes('mantine-datatable')) {
            return 'vendor-mantine';
          }
          if (id.includes('recharts')) {
            return 'vendor-charts';
          }
          if (id.includes('@tanstack/react-query')) {
            return 'vendor-query';
          }
          return 'vendor-misc';
        },
      },
    },
  },
});
