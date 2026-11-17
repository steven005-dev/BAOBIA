import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// HTTPS local pour le téléphone (la caméra exige HTTPS) : seulement avec
// `npm run dev:phone` (mode « phone ») et si `npm run cert` a créé .certs/.
// `npm run dev` reste toujours en HTTP sur http://localhost:5173.
const certDir = fileURLToPath(new URL('./.certs/', import.meta.url))
function phoneHttps() {
  if (!existsSync(`${certDir}cert.pem`) || !existsSync(`${certDir}key.pem`)) {
    throw new Error("Certificat absent : lancez d'abord « npm run cert ».")
  }
  return { cert: readFileSync(`${certDir}cert.pem`), key: readFileSync(`${certDir}key.pem`) }
}

const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const https = mode === 'phone' ? phoneHttps() : undefined
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: { https, proxy },
    preview: { https, proxy },
  }
})
