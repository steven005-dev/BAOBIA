import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// HTTPS local (test sur téléphone : la caméra exige HTTPS). Activé seulement si
// `npm run cert` a créé .certs/ ; sinon HTTP comme avant.
const certDir = fileURLToPath(new URL('./.certs/', import.meta.url))
const https =
  existsSync(`${certDir}cert.pem`) && existsSync(`${certDir}key.pem`)
    ? { cert: readFileSync(`${certDir}cert.pem`), key: readFileSync(`${certDir}key.pem`) }
    : undefined

const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { https, proxy },
  preview: { https, proxy },
})
