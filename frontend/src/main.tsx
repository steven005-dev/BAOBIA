import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
// Titres et boutons (charte v2) : Lexend, pensée pour la lisibilité ; seulement latin (poids léger).
import '@fontsource/lexend/latin-500.css'
import '@fontsource/lexend/latin-700.css'
import './styles/globals.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/service-worker.js').catch(() => {
      // L'application reste utilisable en ligne même si le navigateur refuse le cache hors ligne.
    })
  })
}
