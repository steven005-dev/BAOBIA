# BAOBIA : comment on travaille ensemble

Règles de travail de l'équipe pour le prototype. Elles sont simples volontairement : le but est d'avancer vite sans se marcher dessus.

Voir aussi : `GUIDE_COMMANDES.md` (les commandes), `BAOBIA_UI_GUIDELINES.md` (l'interface), la fiche technique et le cahier des charges (PDF).

---

## 1. Les principes

1. **Un seul dépôt** pour l'application (`backend/` et `frontend/`). La maquette 3D de Yéné a son propre dépôt.
2. **Chacun possède des modules complets** (backend + écrans), pas une couche technique.
3. **On fusionne souvent, par petites demandes.** Une branche qui dure plusieurs jours crée des conflits énormes.
4. **`main` contient toujours du code qui marche.** On n'y envoie jamais directement.
5. **La simplicité de l'interface prime** : les utilisateurs sont peu lettrés, sur téléphone modeste, avec une connexion instable.
6. **Aucun secret, aucune donnée réelle** dans le dépôt. Les données de démonstration sont simulées et marquées comme telles.

---

## 2. Qui possède quoi

| Personne | Modules (backend et frontend) | Autres responsabilités |
|---|---|---|
| Chef de projet | `accounts`, `identity`, `audit`, `notifications` | Socle, composants partagés et thème (`frontend/src/components`, `styles`), `infra/`, `docs/`, intégration, relecture de tout ce qui touche l'interface, démonstration |
| Konan Romuald | `traceability` (mouvements), `sync`, et côté React `movements`, `offline` | Application installable (PWA), hors ligne, tests de faisabilité sur téléphone |
| Yéo | `health`, `alerts`, `geo`, et côté React `health`, `alerts`, `map` | Moteur d'exposition, règles sanitaires en table, carte |
| Yéné | Dépôt séparé `baobia-demo3d` | Maquette 3D de présentation |

Le fichier `.github/CODEOWNERS` applique ces responsabilités : GitHub demande automatiquement la relecture du responsable concerné.

**Règle de frontière.** Un module peut **lire les identifiants** d'un autre module (un mouvement référence l'identifiant d'un animal), mais il ne modifie jamais directement ses tables. Il passe par les fonctions publiques du fichier `services.py` de l'autre module. Si la fonction dont vous avez besoin n'existe pas, demandez-la à son responsable.

---

## 3. Le cycle d'une tâche

1. **La tâche existe** dans l'onglet Issues / Projects de GitHub (une carte, une étiquette de module).
2. **Je la prends** : je me l'assigne et je la passe en « En cours ».
3. **Je crée ma branche** à partir de `main` à jour : `feature/<module>-<sujet>`.
4. **Je code** en petits morceaux, avec des commits clairs.
5. **Avant d'ouvrir la demande**, je mets ma branche à jour avec `main` et je teste.
6. **J'ouvre une demande de fusion** (Pull request), je remplis le modèle (ce que ça fait, module, vérifications).
7. **Quelqu'un la relit** (voir section 5). Je corrige si on me le demande.
8. **Elle est fusionnée** dans `main`. Je supprime ma branche. La tâche passe en « Terminé ».

**Une demande de fusion = une fonction terminée et testable.** Pas de demande « à moitié finie ».

---

## 4. Les branches et les commits

- Noms de branche : `feature/<module>-<sujet>`, par exemple `feature/movements-confirmation`. Pour une correction : `fix/<module>-<sujet>`.
- Messages de commit : `module: ce qui a été fait`, par exemple `identity: ajoute le modèle Animal`.
- Un commit = un changement cohérent. Pas de « modif », « test », « wip ».
- On ne réécrit jamais l'historique de `main` (pas de `push --force`).

---

## 5. Les relectures (revue de code)

- **Relecture circulaire** : le chef de projet relit Romuald, Romuald relit Yéo, Yéo relit le chef de projet.
- **Le chef de projet relit en plus** tout ce qui touche l'interface (composants, textes, couleurs).
- **Délai** : une demande de fusion est relue dans la **demi-journée**. Une relecture qui traîne bloque tout le monde.
- **Ce qu'on vérifie** : ça fait ce que la tâche demande ; ça respecte les frontières entre modules ; pas de secret ni de donnée réelle ; aucune règle sanitaire écrite en dur (les règles sont dans la table prévue) ; interface conforme à la charte.
- Les remarques sont **sur le code, pas sur la personne**, et précises : « à cette ligne, voici le problème et une piste ».

---

## 6. Règles par domaine

### Base de données et migrations
- **Chaque personne crée des migrations uniquement pour ses applications.**
- Avant de fusionner, on met sa branche à jour pour éviter deux migrations en conflit.
- Les événements (mouvements, signalements, corrections) sont **en ajout seul** : une correction crée un nouvel enregistrement, elle ne modifie pas l'ancien.
- Les identifiants des enregistrements sont des **UUID** créés par l'appareil, pour que le hors ligne fonctionne.

### API
- Chaque route est documentée dans le schéma de l'API **avant** de coder l'écran qui l'utilise.
- Les droits sont vérifiés **côté serveur** à chaque route. Les réponses sont masquées selon le profil : un éleveur exposé ne reçoit jamais l'identité de l'élevage d'origine.

### Interface (frontend)
- Les couleurs, tailles et rayons viennent **des variables du thème** (`globals.css`). Aucune couleur écrite à la main.
- On utilise les composants du dossier `components/` ; s'il en manque un, on le demande au chef de projet ou on le crée dans le kit avec son accord.
- Les mots de l'interface suivent le vocabulaire officiel de la charte (Signaler, Confirmer, Valider…). Pas de nouveau mot sans accord.
- Toute action écrit **d'abord en local** puis dans la file d'envoi (`offline/`) : l'interface ne dépend jamais d'une réponse du serveur.
- Chaque écran passe le test de simplicité de la charte (8 questions).

### Règles sanitaires et données
- Valeurs de période, seuil et profondeur : **dans la table de règles**, jamais dans le code.
- Données de démonstration : toujours marquées « simulées ».

---

## 7. Communication

- **Point quotidien de 15 minutes**, à heure fixe : ce que j'ai fait hier, ce que je fais aujourd'hui, ce qui me bloque.
- **Un seul canal de discussion** pour l'équipe (groupe de messagerie), un fil par sujet quand c'est possible.
- **Blocage de plus d'une demi-journée** : on le dit immédiatement, sans attendre le point suivant. Le lot le plus en retard reçoit de l'aide en priorité.
- **Toute décision** qui change le périmètre, le vocabulaire, les couleurs ou le scénario de la maquette est **écrite** (dans `docs/` ou sur la carte de la tâche) et annoncée à toute l'équipe, **y compris à Yéné**.

---

## 8. Calendrier indicatif

Dates à recaler après les tests de faisabilité.

| Date | Jalon |
|---|---|
| 6 nov. | Squelette du dépôt ; modèles minimaux d'identité et données de test (par le chef de projet) ; structure des tables mouvements validée (Romuald et Yéo) |
| 7 nov. | Fonction unique d'écriture hors ligne livrée (Romuald) ; tests de faisabilité sur téléphone réel |
| 8 nov. | Identité complète : centres, animaux, étiquettes, scan, fiche |
| 9 nov. | Maquette 3D, version 1 (Yéné) |
| 11 nov. | Mouvements, double confirmation, rapprochement |
| 14 nov. | Santé et alertes de bout en bout ; maquette 3D, version 2 |
| 16 nov. | Carte et tableaux de bord |
| 17 nov. | Maquette 3D, version 3 et vidéo de secours |
| 18 nov. | **Gel des nouvelles fonctions** : seulement des corrections |
| 19 nov. | Répétition générale et plan de secours |
| 20 nov. | Présentation |

---

## 9. Définition de « terminé »

Une fonction est terminée quand :
- elle marche sur un téléphone réel (ou une simulation mobile) ;
- elle est testée, et le cas d'erreur est géré ;
- les droits et le masquage des données sont vérifiés côté serveur ;
- elle respecte la charte et le vocabulaire ;
- elle fonctionne hors ligne si elle fait partie du parcours terrain ;
- aucune règle sanitaire n'est écrite en dur, aucune donnée réelle ni secret n'est dans le code ;
- elle a été relue et fusionnée dans `main`.

---

## 10. Si le temps manque

On protège d'abord **le parcours de démonstration** : enregistrer un animal, le transférer avec double confirmation, signaler un cas, voir l'alerte expliquée (avec le cas négatif), voir la carte. Les ajouts passent après. Sacrifier dans cet ordre (le premier à abandonner d'abord) : tableau de bord d'administration, détail de zone enrichi, carnet sanitaire complet, indicateur de complétude. **Ne jamais sacrifier** : signalement, moteur d'exposition, cas négatif, masquage par profil, carte simple.

---

## 11. Ce qu'on ne fait pas

- Pas de commit direct sur `main`.
- Pas de `push --force`.
- Pas de secret, de mot de passe ou de donnée réelle dans le dépôt.
- Pas de modification des modèles ou des migrations d'un autre module sans prévenir son responsable.
- Pas de nouvelle bibliothèque importante sans en parler à l'équipe (poids, licence, compatibilité).
- Pas de couleur ou de mot d'interface inventé hors de la charte.