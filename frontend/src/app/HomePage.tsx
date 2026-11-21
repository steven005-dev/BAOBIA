/**
 * Accueil (charte, section 7) : les grandes actions du terrain en tuiles. Chaque tuile
 * mène à l'écran du module concerné. Pas de logique métier ici.
 */

import { ArrowLeftRight, CirclePlus, Flag, KeyRound, LogOut, PackageCheck, QrCode, UserPlus } from 'lucide-react'
import { Navigate, useNavigate } from 'react-router'

import { useAuth } from '@/auth/AuthProvider'
import { BigChoiceTile } from '@/components/BigChoiceTile'
import { Button } from '@/components/Button'
import { UnreadMessages } from '@/features/notifications/UnreadMessages'
import { mots, titres } from '@/lib/vocabulaire'

export function HomePage() {
  const { user, logout, hasRole } = useAuth()
  const navigate = useNavigate()
  // Vétérinaire et autorité : pas d'Accueil terrain, on ouvre les alertes (charte, section 7).
  if (hasRole('veterinarian') || hasRole('authority')) return <Navigate to="/alertes" replace />
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title font-bold text-foreground">{user?.full_name ?? mots.accueil}</h1>
      <UnreadMessages />
      <div className="grid grid-cols-2 gap-3">
        <BigChoiceTile to="/centres" icon={CirclePlus} label={mots.ajouter} />
        <BigChoiceTile to="/mouvements" icon={ArrowLeftRight} label={mots.transferer} />
        <BigChoiceTile to="/mouvements/recevoir" icon={PackageCheck} label={mots.recevoir} />
        <BigChoiceTile to="/sante" icon={Flag} label={mots.signaler} />
        {hasRole('field_agent') && <BigChoiceTile to="/eleveurs/nouveau" icon={UserPlus} label={mots.inscrire} />}
        {hasRole('field_agent') && <BigChoiceTile to="/etiquettes" icon={QrCode} label={mots.etiquettes} />}
      </div>
      <Button variant="ghost" icon={KeyRound} onClick={() => navigate('/mot-de-passe')} className="self-center">
        {titres.changerMotDePasse}
      </Button>
      <Button variant="ghost" icon={LogOut} onClick={() => void logout()} className="self-center">
        {mots.quitter}
      </Button>
    </div>
  )
}
