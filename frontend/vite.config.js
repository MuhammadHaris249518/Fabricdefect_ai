import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      // Generated masks / result images are served by the FastAPI backend
      // at "/storage/..." (StaticFiles mount in app/main.py). The frontend
      // displays result_url as "/storage/results/..." — without proxying
      // that path, the Vite dev server returns 404 and the generated image
      // never renders in ComparisonView.
      '/storage': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})