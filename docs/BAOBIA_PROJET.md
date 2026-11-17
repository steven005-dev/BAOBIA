# BAOBIA : le projet, son contexte et son architecture

> Document d'entrée pour toute personne (ou tout agent IA) qui rejoint le projet. À lire **avant** les autres documents.
> Version 1.1 - 12 novembre 2026 (ajout du regroupement de zone). Prototype présenté à SELAB 2026 (Abidjan), présentation prévue vers le 20 novembre 2026 (règles détaillées du concours non confirmées).

---

## 1. En une phrase

**BAOBIA aide à retrouver très vite les élevages qui ont reçu des animaux d'un foyer sanitaire suspect, et à les alerter, grâce à une identification simple (étiquette QR), une traçabilité des mouvements et une alerte sanitaire explicable.**

Le nom reprend l'arbre africain emblématique : un repère solide et durable. Quatre piliers :

| Pilier | Ce que ça veut dire |
|---|---|
| **Identifier** | Chaque animal ou lot reçoit un identifiant unique, lisible par QR code et par un code court qui se dicte. |
| **Tracer** | Les déplacements entre élevages, marchés et abattoirs sont déclarés puis confirmés par les deux parties. |
| **Surveiller** | Les éleveurs signalent un cas ; un vétérinaire habilité évalue et valide. |
| **Alerter** | Le système retrouve les élevages **exposés**, explique pourquoi, et notifie les bonnes personnes. |

## 2. Le problème

En Côte d'Ivoire comme dans une grande partie de l'Afrique, le bétail circule beaucoup (foires, marchés, transhumance, ventes entre éleveurs) mais ces mouvements ne sont presque jamais enregistrés. Quand une maladie apparaît :
- on ne sait pas d'où viennent les animaux ni où ils sont allés ;
- l'alerte arrive trop tard, ou pas du tout, aux élevages concernés ;
- on réagit soit trop peu (la maladie se propage), soit trop largement (on bloque des élevages sans raison).

BAOBIA ne prétend pas résoudre toute la santé animale : il rend **retrouvable** le chemin des animaux, pour réagir vite et juste.

## 3. Les utilisateurs et leurs contraintes

| Rôle | Ce qu'il fait |
|---|---|
| **Éleveur** | Enregistre ses animaux, déclare et confirme les mouvements, signale un cas, reçoit les alertes. |
| **Agent de terrain** | Agit pour des éleveurs (par mandat) : enregistrement, étiquetage, signalement. |
| **Vétérinaire habilité** | Évalue les signalements, valide les alertes de niveau 3. **Seul** à pouvoir valider. |
| **Autorité** | Consulte la situation, la carte et les alertes de son périmètre. |
| **Commerçant** | Déclare et confirme des mouvements (achat, vente). |

**Contraintes terrain, qui dictent tout le design :**
- Utilisateurs souvent **peu lettrés** : l'interface est simple, avec peu de texte, des icônes, des gros boutons (60 px).
- **Téléphone modeste** et **connexion instable** : l'application doit fonctionner **hors ligne** et se synchroniser plus tard.
- **Mot d'ordre : la simplicité de l'interface.** Toute fonction qui complique l'écran est suspecte.

## 4. Principes non négociables

1. **Aucune valeur légale.** BAOBIA est un outil d'aide. Il ne remplace ni un certificat, ni un document officiel.
2. **Exposé n'est pas contaminé.** On dit « exposé », « à surveiller », jamais « contaminé » pour un élevage qui a seulement reçu des animaux d'un foyer.
3. **Seul un vétérinaire habilité valide** une alerte de niveau 3. Le système propose, le vétérinaire décide.
4. **Les règles sanitaires sont des données, pas du code** : période d'exposition, profondeur de recherche, seuils sont dans une table (`disease_rule`) versionnée.
5. **Pas de suivi en continu.** La position n'est enregistrée qu'à l'instant d'un scan ou d'une déclaration. Un scan en un lieu ne prouve pas que l'animal y était.
6. **Le QR code ne contient que le code court.** Aucune donnée personnelle ni sanitaire dans l'étiquette.
7. **Double confirmation des mouvements** : l'expéditeur et le destinataire confirment. Les écarts sont tracés (rapprochement).
8. **Règle de visibilité** : un éleveur exposé reçoit un **message neutre**, sans l'identité de l'élevage d'origine.
9. **Pas de « super administrateur »** côté produit : les droits sont répartis par rôle, périmètre et mandat. (Le compte administrateur de Django est réservé à l'équipe technique.)
10. **L'histoire n'est jamais effacée** : les événements sont en ajout seul, les corrections créent de nouvelles lignes.
11. **Aucun secret ni donnée réelle** dans le dépôt. Les données de démonstration sont marquées « simulées ».

## 5. Périmètre

**Dans le prototype (P1) :** centres d'élevage, identification d'animaux et de lots avec étiquettes QR, scan et fiche, mouvements avec double confirmation et rapprochement, signalement sanitaire, évaluation vétérinaire, regroupement de signalements par zone avec confirmation par les vétérinaires de la zone, moteur d'exposition avec chemin explicable et cas négatif, alertes à 3 niveaux, notifications neutres, carte par zones, fonctionnement hors ligne, journal d'audit.

**Prévu mais pas codé (P2/P3), dont la place est réservée dans la base :** transhumance et retours, déclaration de vol, résultats de laboratoire, enquêtes et quarantaines, détection de doublons, contrôle avant achat, points de contrôle.

**Abandonné volontairement :** puce électronique (RFID) et suivi en temps réel. L'identification se fait **uniquement par étiquette QR** et code court.

## 6. Parcours de démonstration (ce qu'on protège avant tout)

1. Un éleveur **enregistre un animal** et lui pose une étiquette.
2. Il le **transfère** à un autre élevage avec **double confirmation**.
3. Un éleveur **signale un cas** (symptômes cochés, photo).
4. Un vétérinaire habilité **valide** ; l'**alerte** apparaît avec la liste des élevages exposés, **le chemin expliqué**, et **le cas négatif** (pourquoi tel élevage est écarté).
5. La **carte** montre les zones selon 5 états : normal, à surveiller, exposé, alerte, inconnu.

**Second scénario : regroupement de zone.**
1. Plusieurs éleveurs d'une même zone **signalent** des cas similaires sur la même espèce, en quelques jours. Aucun signalement seul ne suffit.
2. Le système **repère le regroupement** par des règles explicables (nombre de signalements, période, part des animaux touchés par rapport à l'effectif connu). Ce n'est pas un diagnostic.
3. Les **vétérinaires habilités de la zone** sont prévenus. L'un d'eux **confirme** ou **infirme**. Sans réponse dans le délai, une relance part.
4. Si c'est confirmé (niveau 3), le système retrouve les **élevages exposés** par les mouvements, en partant des élevages qui ont signalé, et envoie des **messages neutres**.
5. La **carte** change de couleur : à surveiller pendant l'attente, puis exposé et alerte.

**À ne jamais sacrifier :** le signalement, le moteur d'exposition, le cas négatif, le masquage par profil, la carte simple.

## 7. Vocabulaire du produit

| Terme | Sens |
|---|---|
| **Centre** | Un lieu d'élevage, de marché ou d'abattoir. Un détenteur responsable, éventuellement d'autres membres. |
| **Unité suivie** | Ce que l'on suit : soit un **animal** individuel, soit un **lot** (volaille, petits ruminants en groupe). |
| **Étiquette / code court** | Étiquette physique pré-numérotée. Son QR contient un code de 9 caractères (dont 1 de contrôle, sans 0/O/1/I). |
| **Mouvement** | Déplacement d'unités d'un centre à un autre, déclaré puis confirmé par les deux côtés. |
| **Rapprochement** | Comparaison de ce qui a été envoyé et reçu ; les écarts sont enregistrés. |
| **Signalement** | Un éleveur ou agent déclare un cas suspect. |
| **Regroupement de zone** | Plusieurs signalements similaires dans une même zone, pour une même espèce, sur une période, rapportés à l'effectif connu. Il déclenche une alerte que les vétérinaires de la zone confirment ou infirment. Si l'effectif est inconnu, la confiance est réduite et c'est indiqué. |
| **Habilitation** | Preuve qu'un vétérinaire est habilité à valider. |
| **Mandat** | Autorisation donnée à un agent d'agir pour des centres. |
| **Règle sanitaire** | Paramètres d'une maladie (périodes, profondeur, seuil), versionnés. |
| **Exposition** | Un centre ou une unité en lien avec le foyer dans la fenêtre de la règle. Ce n'est **pas** une contamination. |
| **Alerte, niveau 1 / 2 / 3** | 1 = suspicion, 2 = suspicion renforcée, 3 = **validée par un vétérinaire habilité**. |
| **Cas négatif** | Un élevage examiné puis écarté, avec la raison, pour que l'alerte soit explicable. |
| **Zone** | Découpage administratif (région, département...). La carte affiche un état par zone. |

**Mots de l'interface** (voir la charte) : Signaler, Confirmer, Valider... Pas de nouveau mot sans accord.

## 8. Architecture

### 8.1 Vue d'ensemble

```
   Téléphone / navigateur                         Serveur
 ┌───────────────────────────┐          ┌──────────────────────────────┐
 │  Frontend React (PWA)     │  HTTPS   │  Django + Django REST        │
 │  - écrans simples         │ <──────> │  Framework (un seul projet)  │
 │  - stockage local         │   JSON   │  une application par module  │
 │  - file d'envoi hors ligne│   JWT    │  - règles, droits, calculs   │
 └───────────────────────────┘          └──────────────┬───────────────┘
                                                       │
                                         ┌─────────────▼───────────────┐
                                         │ PostgreSQL + PostGIS (Docker)│
                                         └─────────────────────────────┘
```

### 8.2 Choix techniques

| Domaine | Choix |
|---|---|
| Frontend | React + Vite + TypeScript, Tailwind v4, shadcn/ui, lucide-react, **PWA hors ligne d'abord**. Police Atkinson Hyperlegible. |
| Backend | Django + Django REST Framework, authentification JWT, schéma d'API drf-spectacular. |
| Base de données | PostgreSQL 16 + PostGIS, dans un conteneur Docker (`docker-compose.yml`). |
| Identifiants | UUID créés sur l'appareil (le hors ligne fonctionne sans le serveur). |
| Connexion | Par **numéro de téléphone** (modèle utilisateur Django personnalisé). |
| Maquette 3D | Dépôt séparé `baobia-demo3d` (équipe Yéné), pour la présentation. |

### 8.3 Un monolithe modulaire, pas des microservices

Un **seul projet Django**, avec **une application par module** (`backend/apps/<module>`). Ce choix est volontaire : équipe de 3 développeurs, délai court, une seule base, déploiement simple. Chaque module a un responsable ; les modules communiquent par des **fonctions publiques** (`services.py`), jamais en écrivant dans les tables des autres.

| Application | Rôle |
|---|---|
| `core` | Classes de base et catalogue partagé (espèces). |
| `geo` | Zones et états de la carte. |
| `accounts` | Utilisateurs, organisations, rôles, habilitations, mandats, appareils. |
| `identity` | Centres, animaux, lots, étiquettes, vérifications, photos. |
| `traceability` | Mouvements, confirmations, écarts, événements de vie. |
| `health` | Maladies, symptômes, signalements, évaluations, carnet sanitaire. |
| `alerts` | Règles sanitaires, alertes (signalement ou regroupement de zone), décisions des vétérinaires, expositions et leur chemin. |
| `sync` | Opérations hors ligne, conflits, flux de changements. |
| `notifications` | Messages aux utilisateurs. |
| `audit` | Journal d'audit inaltérable. |

Dépendances sans cycle (chaque application ne référence que celles à sa gauche) :
`core <- geo <- accounts <- identity <- traceability, health <- alerts <- notifications`, avec `sync` et `audit` en bout de chaîne.

### 8.4 Arborescence du dépôt

```
baobia/
├── backend/            Django (manage.py, baobia/ = réglages, apps/<module>/, scripts/)
├── frontend/           React (src/features/<module>, src/components, src/styles, offline/)
├── docs/               Documentation (ce fichier, spécification de la base, charte...)
├── infra/              postgres/ (scripts d'initialisation), proxy/
├── .github/            CODEOWNERS, modèle de demande de fusion, workflows
├── docker-compose.yml  Base PostgreSQL + PostGIS
├── .env.example        Variables d'environnement (valeurs factices)
└── README.md
```

### 8.5 Principes d'architecture

- **Événements en ajout seul, état en cache contrôlé.** Un mouvement, une confirmation, un signalement ne se modifient pas ; l'état courant (statut, centre actuel) est un cache calculé, écrit seulement par le module propriétaire.
- **Supertype `tracked_unit`.** Animal et lot partagent un identifiant : toutes les tables pointent vers une seule clé `unit_id`.
- **Garde-fous dans la base** (CHECK, UNIQUE partiels, triggers) : même un bogue de code ne peut pas écrire un état impossible (ex. une alerte de niveau 3 sans vétérinaire habilité est refusée).
- **Hors ligne d'abord** : toute action s'écrit **localement** puis dans une file d'envoi ; l'interface ne dépend jamais d'une réponse du serveur. Rejouer une opération n'a aucun effet (idempotence par UUID).
- **Droits côté serveur** à chaque route, avec **masquage par profil** des réponses.

## 9. Les flux principaux

**Mouvement.** L'éleveur déclare une sortie (les unités sont verrouillées : une unité ne peut être que dans un mouvement ouvert) -> le destinataire confirme avec un code -> à la double confirmation, le centre courant des unités est mis à jour -> un écart éventuel est enregistré (rapprochement).

**Signalement -> alerte.** Deux déclencheurs possibles :
- **Un signalement** : un éleveur signale -> un vétérinaire habilité évalue -> une alerte est créée (niveau 1 ou 2) ou validée (niveau 3).
- **Un regroupement de zone** : plusieurs signalements similaires dans la même zone, même espèce, sur la période de la règle -> le système crée une alerte de zone (niveau 1) -> les vétérinaires habilités de la zone (zones parentes incluses) sont prévenus -> l'un d'eux confirme (niveau 3) ou infirme ; sans réponse dans le délai de la règle, une relance part.

Ensuite, dans les deux cas : le moteur parcourt le graphe des mouvements selon la règle (fenêtres de dates, profondeur), en partant du foyer ou des élevages qui ont signalé -> il écrit les expositions avec leur chemin, **y compris les cas écartés** -> notifications neutres -> la carte est mise à jour.

**Hors ligne.** L'appareil crée ses enregistrements avec leurs UUID et les met en file ; à la reconnexion, le serveur applique les opérations (sans doublon), signale les conflits au lieu d'écraser, et renvoie les changements utiles à cet appareil.

## 10. Sécurité et confidentialité

- Droits par rôle, périmètre et mandat, **toujours vérifiés côté serveur**.
- Mots de passe hachés ; jetons JWT à durée limitée ; limitation des tentatives de connexion.
- Journal d'audit en ajout seul (qui a fait quoi, quand), sans secret.
- Aucune donnée personnelle dans le QR code.
- Identité de l'élevage d'origine **jamais** transmise à un éleveur exposé.
- Seuil minimal d'effectif pour afficher une zone (anonymat sur la carte).
- Aucun secret dans le dépôt ; `.env` jamais envoyé sur GitHub.

## 11. L'équipe et les responsabilités

| Personne | Responsabilités |
|---|---|
| **Chef de projet** | `core`, `accounts`, `identity`, `audit`, `notifications` ; socle frontend (thème, composants partagés) ; infra, documentation, intégration, relecture de tout ce qui touche l'interface, démonstration. |
| **Konan Romuald** | `traceability`, `sync` ; côté React : mouvements et hors ligne (PWA). |
| **Yéo** | `health`, `alerts`, `geo` ; côté React : santé, alertes, carte ; moteur d'exposition. |
| **Yéné** | Maquette 3D de présentation (dépôt séparé `baobia-demo3d`). |

Le fichier `.github/CODEOWNERS` applique ces responsabilités. Méthode de travail : voir `TRAVAIL_EQUIPE.md` (un seul dépôt, petites demandes de fusion, jamais de commit direct sur `main`, relecture circulaire).

## 12. Où trouver quoi

| Besoin | Document |
|---|---|
| Comprendre le projet (ce fichier) | `BAOBIA_PROJET.md` |
| Ce que le produit doit faire, exigences numérotées | Cahier des charges (PDF) |
| Choix techniques détaillés | Fiche technique (PDF) |
| La base de données : tables, contraintes, règles de code | **`BAOBIA_DB_SPEC.md`** (source de vérité) et `BAOBIA_MCD_MLD.pdf` |
| L'interface : couleurs, composants, vocabulaire | `BAOBIA_UI_GUIDELINES.md` et la charte graphique (PDF) |
| Les commandes (Git, Django, npm) | `GUIDE_COMMANDES.md` |
| Comment on travaille ensemble | `TRAVAIL_EQUIPE.md` |
| Démarrer comme développeur | Guide de démarrage développeur (PDF) |
| La maquette 3D | Dossier maquette 3D (PDF) |

**Ordre de lecture conseillé pour un nouveau développeur :** ce fichier -> `GUIDE_COMMANDES.md` -> `TRAVAIL_EQUIPE.md` -> `BAOBIA_DB_SPEC.md` (ses applications) -> la charte si on touche à l'interface.

## 13. Décisions déjà prises (ne pas rediscuter sans raison)

| Décision | Raison |
|---|---|
| QR code uniquement, pas de puce ni de suivi temps réel | Coût, complexité, délai ; le QR suffit pour tracer. |
| Monolithe modulaire (une application Django par module) | Équipe de 3, délai court, une seule base. |
| Un dépôt principal + un dépôt séparé pour la maquette 3D | La maquette est indépendante de l'application. |
| Connexion par numéro de téléphone | Public cible. |
| UUID créés côté appareil | Hors ligne sans collision. |
| Règles sanitaires en table versionnée | Les changer ne demande pas de redéploiement. |
| Regroupement par règles explicables, IA secondaire | Chaque alerte doit dire pourquoi elle existe ; l'IA ne pose aucun diagnostic et seul un vétérinaire habilité valide. |
| Aucune valeur légale | Prototype ; évite toute confusion avec un document officiel. |
| Simplicité d'interface avant tout | Utilisateurs peu lettrés. |

## 14. Calendrier indicatif

Dates à recaler selon l'avancement réel. Gel des nouvelles fonctions le **18 novembre** (seulement des corrections ensuite), répétition générale le 19, présentation vers le **20 novembre 2026**. Si le temps manque, on sacrifie dans cet ordre : tableau de bord d'administration, détail de zone enrichi, carnet sanitaire complet, indicateur de complétude. On ne sacrifie jamais le parcours de la section 6.
