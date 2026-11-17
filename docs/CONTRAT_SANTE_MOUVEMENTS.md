# Contrat santé / alertes ↔ mouvements / hors ligne

> **Statut : proposition de Yéo, en attente de validation par Konan Romuald.** Une fois validé, toute modification passe par une demande de fusion qui met ce fichier à jour.
> Version 0.1 - 17 novembre 2026. Complète `BAOBIA_DB_SPEC.md` (qui fait foi pour les tables).

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
2. **Rejouer** (même modèle que `POST /api/movements/`) : même `id` et même contenu → **200** et le signalement existant ; même `id`, autre contenu → **409** (« À vérifier »).
3. **Erreurs** : 400 (saisie) et 403 (droits) → « À vérifier » ; réseau, session, serveur → reste en attente. Aucun changement nécessaire dans la file.
4. **Photos** : reportées après la démonstration ; si faites, opération séparée envoyée après le signalement.
5. **Évaluation vétérinaire et alertes** : en ligne uniquement (espace bureau), hors file d'envoi.
6. **Téléphone de l'éleveur** : il reçoit seulement des notifications neutres (`notifications`) ; aucune alerte ni chaîne de mouvements n'y est stockée.

## B. Ce que le moteur d'alertes lit dans `traceability` (lecture seule)

1. `movement` : `from_center_id`, `to_center_id`, `status`, `occurred_at` (départ), `received_at` (arrivée ; si vide, `occurred_at`).
2. `movement_item` : `unit_id`, `quantity_received`, `received_unit_id` (lignée des lots fractionnés) ; `tracked_unit.origin_unit_id`.
3. Statuts : `confirmed` et `partial` comptent toujours ; `declared` seulement si la règle a `include_unconfirmed` ; `cancelled` et `expired` jamais. **À valider :** `disputed` compte, avec une confiance réduite.
4. Mouvement sans `to_center` (hors système) : aucune exposition, affiché au vétérinaire comme « sortie vers l'extérieur ».
5. Engagements : traceability ne renomme pas ces champs ni ces statuts sans demande de fusion `schema:` ; alerts n'écrit dans aucune table de traceability et ne bloque aucun mouvement (quarantaine = P2).

## C. Données de démonstration attendues

Mouvements datés : A → B dans la fenêtre de la règle, puis B → C après l'arrivée à B (exposition de profondeur 2) ; A → D bien avant la fenêtre (cas négatif). À ajouter au seed de traceability, ou fonction de `traceability.services` à appeler depuis le seed d'alerts.
