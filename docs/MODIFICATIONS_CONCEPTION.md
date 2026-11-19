# BAOBIA : modifications de conception (19/11/2026)

> Décidé par le chef de projet. À lire par Romuald et Yéo **avant** de continuer à coder.
> Les détails des tables (noms de colonnes, contraintes) seront dans **la spec v1.4**
> (`docs/BAOBIA_DB_SPEC.md`), qui reste la source de vérité. En cas de doute : demander, ne pas improviser.

## Pourquoi on change maintenant

Le code n'est pas fini : c'est le moment de corriger la conception, après ce sera beaucoup plus cher.
En relisant le système, nous avons trouvé des choix qui ne tiennent pas sur le terrain :

1. **Les ventes passent surtout par les marchés et des intermédiaires**, souvent sans smartphone des deux côtés.
   Exiger la double confirmation pour qu'un transfert existe = la plupart des mouvements ne seront jamais
   enregistrés, donc le traçage des exposés ne marche pas.
2. **Beaucoup d'éleveurs n'ont pas de smartphone** ou lisent mal le français. L'application devient d'abord
   un outil de **professionnels** (agents, gestionnaires de marché, vétérinaires, autorité). L'éleveur est
   inscrit par l'agent (déjà fait) et recevra plus tard ses alertes par SMS.
3. **Une étiquette imprimée sur place ne tient pas** (pas d'imprimante, papier fragile). Voie principale :
   **boucles d'oreille préimprimées** distribuées par lots aux agents ; le code créé par le téléphone reste en secours.
4. **On ne détecte rien tôt** : aujourd'hui on retrouve les exposés *après* la confirmation du vétérinaire.
   Il faut une **surveillance par signes simples** (morts, malades, gros symptômes) comparés à la normale de la zone.
5. **L'Autorité (le vrai client) n'a pas de vue d'ensemble** : pas de flux, carte sans tracés.

Ce qui ne change pas : exposé ≠ contaminé, seul un vétérinaire habilité valide, messages neutres sans nom
d'élevage d'origine, pas de super administrateur, événements en ajout seul, UUID créés sur l'appareil,
règles explicables (pas d'IA qui pose un diagnostic).

## Objectif pour dimanche (22/11)

**Une seule boucle, complète :** identifier → déplacer → signaler → alerter les exposés → voir sur la carte.
Le reste de ce document est présenté au jury comme la conception cible (« prochaine étape »).

---

## Romuald : traçabilité (mouvements)

### Pour dimanche

**R1. Un transfert déclaré d'un seul côté compte, avec un niveau de confiance.**
- Aujourd'hui : un transfert non confirmé par le destinataire n'existe pas pour le reste du système.
- Demain : chaque mouvement a une **confiance** :
  - `confirmed` (« sûr ») : déclaré par l'expéditeur ET confirmé par le destinataire ;
  - `one_side` (« probable ») : déclaré par un seul des deux (expéditeur, destinataire ou agent).
- La double confirmation reste le meilleur cas, mais n'est plus obligatoire pour que le mouvement existe.
- Le moteur d'exposition (Yéo) lit cette confiance : prévoir une fonction de service qui la donne
  (ex. `traceability.services.movements_for_exposure(...)` avec la confiance de chaque mouvement).
- Le nom exact du champ sera dans la spec v1.4.

**R2. Saisie au marché : Entrée / Sortie.**
- Un agent ou un gestionnaire de marché scanne les animaux qui **entrent** dans un marché et qui en **sortent**.
- Le marché est déjà un centre (`center_type = 'market'`). Un passage au marché = deux mouvements
  (origine → marché, marché → destination), confiance `one_side` si l'autre partie ne confirme pas.
- Écran : « Marché » avec deux gros boutons **Entrée** / **Sortie**, puis scan des étiquettes (plusieurs à la suite).
- Droits : membre du centre marché ou mandat `move` sur ce centre (permissions existantes).

### Après dimanche

**R3. API des flux entre zones (chiffres agrégés).** Ex. « zone A → zone B : 120 bovins ce mois-ci ».
Aucun nom d'élevage, seuil minimal d'effectif pour ne pas identifier un élevage. Lue par le tableau de bord
de l'Autorité (Yéo).

**R4.** Ce qui était déjà prévu : rapprochement des écarts, division de lot, module de synchronisation,
textes via `vocabulaire.ts`, heure de l'appareil (`received_at`).

---

## Yéo : santé, alertes, carte

### Pour dimanche

**Y1. Le formulaire Signaler devient « comptable ».**
- Déjà dans le contrat (`CONTRAT_SANTE_MOUVEMENTS.md`) : `report_kind`, `affected_count`, `symptom_codes`,
  `subjects`. À ajouter : **séparer le nombre de morts et le nombre de malades** (au lieu d'un seul
  `affected_count`), et rapporter ce nombre à l'effectif de l'élevage. Photo : après dimanche.
- Une question par écran, gros boutons, compteurs (`NumberStepper`) : même gabarit que « Ajouter un animal ».
- Ces chiffres servent à la détection précoce (Y5). Les colonnes exactes seront dans la spec v1.4.

**Y2. Le calcul d'exposition tient compte de la confiance des mouvements (R1).**
- Mouvement `confirmed` : comme aujourd'hui.
- Mouvement `one_side` : l'élevage est aussi « contact possible », mais **l'alerte l'indique** (ex. « transfert
  déclaré d'un seul côté ») pour que le vétérinaire juge. Le message à l'éleveur reste le même, neutre.

**Y3. Carte au niveau du département.**
- Charger les **tracés officiels** des départements de Côte d'Ivoire dans `zone.boundary`, et le centre
  (`centroid`) pour l'affichage.
- Sans tracés, il n'y a pas de carte : c'est prioritaire pour la démo.
- Niveau « département » : **à confirmer par le chef de projet** (sinon région).

**Y4. Écrans vétérinaire** : liste des signalements de sa zone, évaluation (valider / refuser), alerte avec
les élevages exposés, le chemin et le cas négatif. Le serveur est déjà prêt.

**Y5. Petit ajout serveur pour la fiche de l'animal** : lister les signalements d'**un animal**
(filtre `unit_id` sur `/api/health-reports/`, mêmes règles de visibilité). Le chef de projet affiche ensuite
une partie « Santé » sur la fiche de l'animal.

### Après dimanche

**Y6. Signal « à surveiller » (regroupement de zone, version simple).** Comparer les morts et les malades
déclarés dans une zone sur une période à la **normale de cette zone** ; au-dessus d'un seuil, signal
« à surveiller » aux vétérinaires de la zone, qui confirment ou infirment. Règles écrites et explicables ;
un modèle d'IA de détection d'anomalies viendra seulement quand il y aura de vraies données.

**Y7. Tableau de bord national de l'Autorité** : carte, alertes, flux entre zones (API R3). Pas de super
administrateur : c'est le rôle Autorité, sur son périmètre (le pays pour l'autorité nationale).

**Y8. Carnet de vaccination** de l'animal (vaccinations, rappels).

---

## Chef de projet : identité, comptes, spec

### Pour dimanche
- **C1. Spec v1.4** : inscrire toutes ces décisions (colonnes, contraintes) et prévenir l'équipe.
- **C2. Boucles préimprimées** comme voie principale : à l'ajout d'un animal, **scanner la boucle** déjà
  remise par l'agent ; le code créé par le téléphone devient le secours.
- **C3. Partie « Santé » sur la fiche de l'animal** (avec Y5).
- Fait le 19/11 : **l'agent de terrain inscrit l'éleveur** et son élevage (pas d'inscription libre).

### Après dimanche
- **C4. Passeport de l'animal** : page de vérification par QR pour un acheteur (origine, état sanitaire,
  vaccinations), sans nom d'élevage.
- **C5. Alertes par SMS** pour les éleveurs sans smartphone.
- **C6. Changement de mot de passe** de l'éleveur.

---

## Ordre de travail

1. **Chef de projet** : spec v1.4 (colonnes de R1, Y1, Y3). Prévient dès qu'elle est fusionnée.
2. **En attendant la spec**, on peut déjà faire ce qui ne touche pas aux tables :
   - Romuald : écran Marché (R2) avec les mouvements actuels ;
   - Yéo : écrans vétérinaire (Y4), chargement des tracés (Y3), filtre `unit_id` (Y5).
3. **Après la spec** : migrations et code de R1, Y1, Y2.
4. **Samedi 21/11** : répétition de la démo de bout en bout, tous ensemble.

Une question, un doute ou un désaccord sur ce document : le dire au chef de projet **avant** de coder.
