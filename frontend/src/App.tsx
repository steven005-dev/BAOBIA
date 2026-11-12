import { useState } from 'react'
import { DeclareMovementForm } from './features/movements/DeclareMovementForm'
import { Warehouse } from 'lucide-react'

export default function App() {
  const [, setSuccessCount] = useState(0)

  return (
    <div className="min-h-screen bg-[var(--background)] flex flex-col items-center">
      {/* En-tête mobile conforme BAOBIA */}
      <header className="w-full bg-[var(--brand)] text-white p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Warehouse className="w-6 h-6" />
          <h1 className="font-bold text-lg tracking-wide m-0">BAOBIA</h1>
        </div>
        <span className="text-xs bg-white/20 px-2.5 py-1 rounded-full font-semibold">
          Données simulées
        </span>
      </header>

      {/* Zone de contenu principale */}
      <main className="w-full max-w-lg p-4">
        <DeclareMovementForm
          onSuccess={() => {
            setSuccessCount((c) => c + 1)
          }}
        />
      </main>
    </div>
  )
}
