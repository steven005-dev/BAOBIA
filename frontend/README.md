# BAOBIA : application (frontend)

React + Vite + TypeScript, Tailwind CSS v4, composants maison sur la charte (`docs/BAOBIA_UI_GUIDELINES.md`).

## Lancer
```powershell
npm install
npm run dev      # http://localhost:5173 ; /api est relayé vers Django (127.0.0.1:8000)
npm run lint     # règles de la charte comprises (couleurs, tailles, mots interdits)
npm run build
```
En développement, `/composants` montre tous les composants partagés.

## Où mettre quoi
| Dossier | Contenu | Responsable |
|---|---|---|
| `src/app/` | Routeur, mise en page, Accueil, navigation par profil | Chef de projet |
| `src/components/` | Composants partagés de la charte | Chef de projet |
| `src/lib/` | Client API, vocabulaire officiel, codes courts, états sanitaires | Chef de projet |
| `src/offline/` | `submit()` : point d'entrée unique de la file d'envoi hors ligne | Konan Romuald |
| `src/features/<module>/` | Écrans et appels API d'un module, routes dans `routes.tsx` | Responsable du module |

## Règles
- Tous les textes viennent de `src/lib/vocabulaire.ts` (un mot par sens ; nouveaux mots marqués « À VALIDER »).
- Aucune couleur ni taille écrite à la main : variables du thème (`src/styles/globals.css`).
- Lectures : `api.get(...)`. Écritures terrain : `submit(...)` de `@/offline`, avec un UUID créé sur le téléphone.
- Un élevage exposé est « Contact possible », jamais « contaminé ».
