# BAOBIA : modifications de conception (19/11/2026)

> Décidé par le chef de projet. À lire par Romuald et Yéo **avant** de continuer à coder.
> Les détails des tables sont dans **la spec v1.4** (`docs/BAOBIA_DB_SPEC.md`, 20/11), qui reste la source de vérité.
> **Pas de modèle d'IA avant dimanche** (décision du 20/11) : la détection reste par règles ; un modèle viendra avec de vraies données. En cas de doute : demander, ne pas improviser.

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

**R1. Un transfert déclaré d'un seul côté compte : déjà en place, à garder.**
- Bonne nouvelle : le statut `declared` existe et le moteur d'exposition le compte déjà
  (`include_unconfirmed`). **Rien à changer dans les tables.**
- À vérifier de ton côté : un transfert reste `declared` (il n'expire pas en silence) tant que le
  destinataire n'a pas confirmé, et l'écran le montre « En attente » chez l'expéditeur.

**R2. Saisie au marché : Entrée / Sortie.**
- Un agent ou un gestionnaire de marché scanne les animaux qui **entrent** dans un marché et qui en **sortent**.
- Le marché est déjà un centre (`center_type = 'market'`). Un passage au marché = deux mouvements
  (origine → marché, marché → destination), qui restent `declared` si l'autre partie ne confirme pas
  (spec v1.4, section 9.11). Aucune nouvelle table.
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
- Déjà dans le contrat (`CONTRAT_SANTE_MOUVEMENTS.md`) : `report_kind`, `affected_count`, `symptom_codes`, `subjects`.
- **Seul changement de table (spec v1.4) : `health_report.dead_count`** (dont morts ; `0 <= dead_count <= affected_count`).
  Malades = `affected_count - dead_count`. Une migration, un champ dans l'API et dans le contrat.
- Écran : une question par écran, gros boutons, compteurs (`NumberStepper`), comme « Ajouter un animal » :
  combien de malades ? combien de morts ? quels gros symptômes ? Photo : après dimanche.

**Y2. Confiance réduite aussi pour un transfert `declared` (petit changement).**
- Aujourd'hui `compute_exposures` met `alert.confidence = 'reduced'` seulement pour un mouvement `disputed`.
- Spec v1.4 (9.6) : faire de même pour un mouvement `declared` dans le chemin d'un exposé, et l'afficher au
  vétérinaire (« transfert déclaré d'un seul côté »). Le message à l'éleveur reste le même, neutre. + 1 test.

**Y3. Carte au niveau du département.**
- Charger les **tracés officiels** des départements de Côte d'Ivoire dans `zone.boundary`, et le centre
  (`centroid`) pour l'affichage.
- Sans tracés, il n'y a pas de carte : c'est prioritaire pour la démo.
- Niveau « département » : **à confirmer par le chef de projet** (sinon région).

**Y4. Écrans vétérinaire** : liste des signalements de sa zone, évaluation (valider / refuser), alerte avec
les élevages exposés, le chemin et le cas négatif. Le serveur est déjà prêt.

**Y5. Filtre des signalements par animal : FAIT par le chef de projet le 20/11** (`?unit_id=` sur
`/api/health-reports/`, 1 test, branche `feature/identity-boucle`). Rien à faire, juste le relire.

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
- **C1. Spec v1.4** : faite le 20/11.
- **C2. FAIT (20/11).** Boucles préimprimées comme voie principale : à l'ajout d'un animal, **scanner la boucle** déjà
  remise par l'agent ; le code créé par le téléphone devient le secours.
- **C3. FAIT (20/11).** Partie « Santé » sur la fiche de l'animal.
- Fait le 19/11 : **l'agent de terrain inscrit l'éleveur** et son élevage (pas d'inscription libre).

### Après dimanche
- **C4. Passeport de l'animal** : page de vérification par QR pour un acheteur (origine, état sanitaire,
  vaccinations), sans nom d'élevage.
- **C5. Alertes par SMS** pour les éleveurs sans smartphone.
- **C6. FAIT (20/11).** Changement de mot de passe.
- **Accord de l'éleveur à l'inscription (loi 2013-450) : FAIT (20/11).**

---

## Ordre de travail

1. **Chef de projet** : spec v1.4 — **faite le 20/11** (une seule colonne : `health_report.dead_count`).
2. **En attendant la spec**, on peut déjà faire ce qui ne touche pas aux tables :
   - Romuald : écran Marché (R2) avec les mouvements actuels ;
   - Yéo : écrans vétérinaire (Y4), chargement des tracés (Y3), filtre `unit_id` (Y5).
3. **Dès la fusion de la spec** : migration `dead_count` et Y2 (Yéo).
4. **Samedi 21/11** : répétition de la démo de bout en bout, tous ensemble.

Une question, un doute ou un désaccord sur ce document : le dire au chef de projet **avant** de coder.
