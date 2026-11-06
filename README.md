# BAOBIA

Plateforme de traçabilité et d'alerte sanitaire pour l'élevage en Côte d'Ivoire.

> Prototype réalisé pour SELAB 2026. Les données de démonstration sont simulées et marquées comme telles.
> BAOBIA est un outil complémentaire : il n'a aucune valeur officielle ou juridique.

## Le problème
Après un cas suspect dans un élevage, retrouver rapidement les autres élevages qui ont reçu des animaux du foyer.

## Ce que fait BAOBIA
- **Identifier** : chaque animal porte une étiquette QR qui ne contient que son numéro.
- **Tracer** : transferts entre élevages, confirmés par les deux parties, même hors ligne.
- **Surveiller** : carnet sanitaire et signalement d'un cas suspect.
- **Alerter** : recherche des élevages exposés, validation par un vétérinaire, carte par zones.

## Principe de conception
La simplicité : les interfaces sont pensées pour des utilisateurs peu lettrés, sur téléphone modeste, avec une connexion instable.

## Technologies
- Backend : Django, Django REST Framework, PostgreSQL + PostGIS
- Frontend : React, Vite, TypeScript, Tailwind CSS, shadcn/ui (application web installable, hors ligne)
- Déploiement : Docker Compose
- Maquette 3D de présentation : dépôt séparé `baobia-demo3d`

## Organisation du dépôt
- `backend/` : Django, un projet, une application par module (`backend/apps/`)
- `frontend/` : React, un dossier par module dans `src/features/`
- `infra/` : base de données, serveur
- `docs/` : cahier des charges, fiche technique, charte graphique

## Installation
Les instructions de lancement seront ajoutées après le lot 0.

## Règles de travail
- Une branche par fonction : `feature/<module>-<sujet>`, jamais de commit direct sur `main`.
- Demande de fusion relue par un autre membre ; le chef de projet relit tout ce qui touche l'interface.
- Aucun secret, aucune donnée réelle dans le dépôt.
- Les couleurs et dimensions viennent des variables du thème (voir `docs/BAOBIA_UI_GUIDELINES.md`).

## Licence
À définir. En attendant, tous droits réservés.