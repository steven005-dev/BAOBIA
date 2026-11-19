# Contrat santé / alertes ↔ mouvements / hors ligne

> **Statut : validé par Yéo et Konan Romuald (19 novembre 2026), sauf la section C en cours de réalisation.** Une fois validé, toute modification passe par une demande de fusion qui met ce fichier à jour.
> Version 0.2 - 19 novembre 2026. Complète `BAOBIA_DB_SPEC.md` (qui fait foi pour les tables).

## A. Ce que la file d'envoi hors ligne transporte pour la santé

1. **Une seule opération hors ligne en P1 : `health_report.submit`**, `POST /api/health-reports/`.

   | Champ | Type | Obligatoire | Remarque |
   |---|---|---|---|
   | `id` | UUID | oui | UUID de l'opération, créé sur le téléphone = identifiant du signalement |
   | `center_id` | UUID | oui | élevage concerné |
   | `report_kind` | `suspicion`, `death`, `abnormal_mortality` | oui | |
   | `affected_count` | entier ≥ 1 | oui | |
   | `self_severity` | `low`, `medium`, `high` | oui | gravité estimée par l'éleveur |
   | `occurred_at` | date-heure ISO | oui | date d'observation, selon le téléphone |
   | `note` | texte ≤ 500 | non | |
   | `latitude`, `longitude` | décimal | non | les deux ou aucun |
   | `position_accuracy_m` | décimal | non | |
   | `position_source` | `gps`, `network`, `manual`, `none` | non | forcé à `none` sans position |
   | `symptom_codes` | liste de codes | non | codes de `GET /api/symptoms/?species=` |
   | `subjects` | liste de `{unit_id, condition}` | non | `condition` : `sick`, `dead`, `suspect`, `contact` ; chaque unité doit être dans l'élevage |

   Symptômes et animaux partent **dans la même opération**.
2. **Rejouer** (même modèle que `POST /api/movements/`) : même `id` et même contenu → **200** et le signalement existant ; même `id`, autre contenu → **409** (« À vérifier »). La comparaison porte sur **tout** le contenu : auteur, élevage, champs, date d'observation, note, position, symptômes, animaux et leur état.
3. **Erreurs** : 400 (saisie) et 403 (droits) → « À vérifier » ; réseau, session, serveur → reste en attente. Aucun changement nécessaire dans la file.
4. **Photos** : reportées après la démonstration ; si faites, opération séparée envoyée après le signalement.
5. **Évaluation vétérinaire et alertes** : en ligne uniquement (espace bureau), hors file d'envoi.
6. **Téléphone de l'éleveur** : il reçoit seulement des notifications neutres (`notifications`) ; aucune alerte ni chaîne de mouvements n'y est stockée.

## B. Ce que le moteur d'alertes lit dans `traceability` (lecture seule)

1. `movement` : `from_center_id`, `to_center_id`, `status`, `occurred_at` (départ), `received_at` (arrivée = `occurred_at` envoyé par la confirmation ; si vide, `occurred_at` du départ).
2. `movement_item` : `unit_id`, `quantity_received`, `received_unit_id` (lignée des lots fractionnés) ; `tracked_unit.origin_unit_id`.
3. Statuts : `confirmed` et `partial` comptent toujours ; `declared` seulement si la règle a `include_unconfirmed` ; `cancelled` et `expired` jamais ; `disputed` compte (prudence) et passe l'alerte en confiance réduite (`alert.confidence = 'reduced'`).
4. Mouvement sans `to_center` (hors système) : aucune exposition, affiché au vétérinaire comme « sortie vers l'extérieur ».
5. Engagements : traceability ne renomme pas ces champs ni ces statuts sans demande de fusion `schema:` ; alerts n'écrit dans aucune table de traceability et ne bloque aucun mouvement (quarantaine = P2).

## C. Données de démonstration (commande séparée de traceability)

Commande séparée (par exemple `seed --demo-traceability`), lancée après `seed --demo`, `seed_health` et `seed_alerts`. Mouvements **bovins** (espèce commune), marqués simulés, datés **par rapport au jour où la commande est lancée** :

| Mouvement | Date | Statut | Rôle dans la démo |
|---|---|---|---|
| A → B | il y a 5 jours | `confirmed` | exposé, profondeur 1 |
| B → C | il y a 3 jours (après l'arrivée à B) | `confirmed` | exposé, profondeur 2 |
| A → D | il y a 60 jours | `confirmed` | **cas négatif** : hors fenêtre |

- Fenêtre utilisée : règle de démonstration `seed_alerts` (**21 jours** avant l'observation du signalement, 0 après, profondeur 3). A → D doit donc dater de plus de 21 jours avant le jour de la démonstration : 60 jours laisse de la marge si la commande est lancée la veille. A → B et B → C doivent rester dans les 21 jours : moins de 10 jours laisse de la marge.
- Le signalement est fait **pendant la démonstration**, à l'élevage A, sur un bovin.
- D : nouvel élevage à créer par `identity.services.create_center`, dans une zone qui compte déjà au moins un autre élevage (seuil d'affichage de la carte : 2 élevages par zone en démonstration), sinon la zone de D sera grisée.
- Lots fractionnés : **non requis** pour la démonstration (reporté).
