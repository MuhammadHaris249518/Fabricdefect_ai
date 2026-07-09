import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // TODO: replace with your current ngrok URL from the Camber
        // notebook (`print(public_url)`). This can change if the tunnel
        // restarts, so re-check it if the frontend starts getting
        // connection errors after a Camber session restart.
        target: 'https://happening-rage-snowfield.ngrok-free.dev',
        changeOrigin: true,
        secure: false,
      },
      // Generated masks / result images are served by the FastAPI backend
      // at "/storage/...' (StaticFiles mount in app/main.py). The frontend
      // displays result_url as "/storage/results/...' — without proxying
      // that path, the Vite dev server returns 404 and the generated image
      // never renders in ComparisonView.
      '/storage': {
        target: 'https://happening-rage-snowfield.ngrok-free.dev',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})