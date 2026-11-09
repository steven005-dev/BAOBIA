import { useEffect, useState } from 'react'
import { getHealth } from './lib/api'
import './App.css'

function App() {
  const [status, setStatus] = useState('Connexion en cours...')

  useEffect(() => {
    getHealth()
      .then(() => setStatus('Backend connecté'))
      .catch(() => setStatus('Backend injoignable'))
  }, [])

  return <main className="health-page"><h1>{status}</h1></main>
}

export default App
