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

## Tester sur un téléphone (caméra = HTTPS obligatoire)
```powershell
npm run cert        # une fois : certificat local dans .certs/ (30 jours, jamais sur GitHub)
npm run dev:phone   # HTTPS, visible sur le Wi-Fi ; Django doit tourner sur ce PC
```
Sur le téléphone, même Wi-Fi : `https://<adresse-IP-du-PC>:5173` (adresse affichée par Vite).
Premier accès : avertissement de sécurité, « Paramètres avancés » puis « Continuer ».
Si le pare-feu Windows le demande, autoriser Node.js sur les réseaux privés.
`npm run dev` reste en HTTP (http://localhost:5173) pour travailler sur le PC.

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
