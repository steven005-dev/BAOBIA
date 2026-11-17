# BAOBIA : spécification de la base de données (source de vérité pour les agents)

> **Version 1.2 - 12 novembre 2026. Ce fichier fait foi.** Il décrit les 56 tables de la base, leurs contraintes et la façon de les coder avec Django.
> Tout agent (ou personne) qui écrit des modèles, des migrations, des services ou des API **doit s'y conformer**. En cas de doute ou de conflit avec du code existant : **ne pas improviser, signaler**.
> Document complémentaire pour les humains : `BAOBIA_MCD_MLD.pdf` (schémas MCD).

### Historique des versions

| Version | Date | Changements |
|---|---|---|
| 1.2 | 12 novembre 2026 | Regroupement de zone : colonnes `cluster_*` et `escalation_hours` dans `disease_rule` ; `trigger_kind`, `species_id`, `confidence`, `escalation_due_at` dans `alert` (`focus_center_id` devient NULL pour une alerte de zone) ; nouvelle table `alert_review` (56 tables) ; nouveaux types d'`alert_event` ; section 9.9 ; décision D11 à trancher. |
| 1.1 | 9 novembre 2026 | Version de référence (55 tables). |

## 0. Comment utiliser ce fichier

1. Lis les sections 1 à 5 en entier avant d'écrire la moindre ligne.
2. Code **uniquement les applications qui te sont assignées** (section 3).
3. Chaque table de la section 6 devient **un modèle Django** avec `db_table` explicite (le nom de la table indiqué).
4. Ne change **jamais** un nom, un type, une contrainte ou une relation de ce fichier sans qu'une demande de fusion `schema:` ait modifié ce fichier d'abord.
5. Si une règle te semble impossible à coder ou fausse, écris-le dans la demande de fusion ; ne contourne pas.

## 1. Contexte en 8 lignes

BAOBIA identifie (étiquettes QR), trace et protège le bétail ivoirien : un éleveur signale un cas, un vétérinaire habilité valide, le système retrouve les élevages **exposés** (jamais « contaminés ») avec le chemin explicable, et alerte. Utilisateurs souvent peu lettrés, téléphone modeste, réseau instable : **application hors ligne d'abord** (les identifiants sont créés sur l'appareil). Prototype sans valeur légale. Stack : Django + DRF, PostgreSQL 16 + PostGIS (Docker), React/Vite. Monolithe modulaire : **un projet Django, une application par module** dans `backend/apps/`.

## 2. Règles absolues (ne jamais enfreindre)

1. **Clés primaires `uuid`** (pas d'entier auto) sauf `change_feed.seq` et `audit_log.id` (`bigint` identité). Un enregistrement créé hors ligne garde son UUID.
2. **Les événements ne se modifient ni ne se suppriment** (liste en section 5.2). Une correction = nouvelle ligne (si la table a le bloc COR). Aucun `UPDATE`/`DELETE` sur ces tables, ni en Python ni en SQL.
3. **Les colonnes marquées CALCULÉ ou « cache »** ne sont écrites que par le fichier `services.py` de l'application propriétaire, dans la même transaction que l'événement qui les justifie. Jamais par un formulaire, un sérialiseur ou une autre application.
4. **Une application ne modifie jamais les tables d'une autre.** Elle appelle les fonctions publiques de `services.py` de l'autre application. Elle peut *lire* ses identifiants.
5. **Aucune règle sanitaire en dur** (période d'exposition, profondeur, seuils) : tout vient de `disease_rule`. Interdit : `if days > 14`.
6. **Exposé n'est pas contaminé** : le vocabulaire du code, de l'API et de l'interface n'emploie jamais « contaminé » pour un élevage exposé.
7. **Seul un vétérinaire habilité valide** une alerte de niveau 3 (`validated_by`, `validated_at`, `habilitation_id` obligatoires, contrôlés par la base **et** le service).
8. **La position n'est enregistrée qu'à l'instant d'un scan ou d'une déclaration** (bloc POS). Jamais de suivi continu. Une position saisie à la main est `manual`.
9. **Visibilité** : un éleveur exposé reçoit un message neutre ; l'identité de l'élevage d'origine n'apparaît dans **aucune** réponse d'API destinée à un éleveur. Les droits sont vérifiés côté serveur à chaque route.
10. **Aucune suppression physique de donnée métier.** On désactive (`is_active`, `ends_at`, statut). Seule exception : `unit_open_movement` (verrou technique).
11. **Aucun secret, aucune donnée réelle** dans le dépôt. Les données de démonstration ont `is_simulated = true`.
12. **Pas de type ENUM PostgreSQL.** États stables = `varchar` + `CHECK ... IN (...)` ; listes qui évoluent = table de catalogue.
13. **Chaque module ne crée de migrations que pour ses propres applications.**

## 3. Applications, propriétaires et dépendances

Dépendances **sans cycle** (une application ne référence que celles à sa gauche) :

```
core <- geo <- accounts <- identity <- traceability, health <- alerts <- notifications
                                  sync (accounts, identity, geo)      audit (accounts)
```

| Application | Responsable | Tables (56 au total) |
|---|---|---|
| `accounts` | Chef de projet | `app_user`, `organization`, `role`, `membership`, `habilitation`, `mandate`, `device` |
| `geo` | Yéo | `zone`, `zone_stat` |
| `core` | Chef de projet | `species` |
| `identity` | Chef de projet | `center`, `center_member`, `center_species`, `tracked_unit`, `animal`, `lot`, `label_batch`, `label`, `identity_support`, `identity_verification`, `ownership_claim`, `subject_photo`, `mandate_center`, `attachment` |
| `traceability` | Konan Romuald | `movement`, `movement_item`, `unit_open_movement`, `movement_confirmation`, `movement_confirmation_code`, `movement_discrepancy`, `movement_status_event`, `status_event` |
| `health` | Yéo | `disease`, `disease_species`, `symptom`, `symptom_species`, `health_event`, `health_report`, `health_report_symptom`, `health_report_subject`, `health_report_attachment`, `health_report_review` |
| `alerts` | Yéo | `disease_rule`, `alert`, `alert_report`, `alert_review`, `alert_exposure`, `alert_exposure_step`, `alert_event`, `investigation`, `quarantine` |
| `sync` | Konan Romuald | `sync_operation`, `sync_conflict`, `change_feed` |
| `notifications` | Chef de projet | `notification` |
| `audit` | Chef de projet | `audit_log` |

- Références entre applications **par texte** : `models.ForeignKey("identity.Center", ...)`, jamais d'import de modèle d'une application située plus à droite.
- `species` est dans `core`, `device` dans `accounts`, `mandate_center` et `attachment` dans `identity` : **volontaire**, pour éviter les cycles de migrations.
- Ordre de création des migrations initiales : `core`, `geo`, `accounts`, `identity`, `traceability`, `health`, `alerts`, `sync`, `notifications`, `audit`.
- **Avant la première migration** : `AUTH_USER_MODEL = "accounts.User"` dans les réglages. Après, le changer oblige à recréer la base.

## 4. Conventions

### 4.1 Noms
- Tables et colonnes en `snake_case` anglais, singulier. `db_table` **explicite** sur chaque modèle (le nom donné en section 6). Classe Django en `PascalCase` (indiquée en section 6).
- Clé étrangère : champ Django `center`, colonne `center_id`. Contraintes nommées : `uniq_<table>_<objet>`, `chk_<table>_<objet>`.

### 4.2 Types SQL -> champs Django
| SQL | Django |
|---|---|
| `uuid` PK | `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` |
| `uuid` FK | `ForeignKey("app.Modele", on_delete=PROTECT)` (`CASCADE` seulement pour les sous-types 1-1 et les liaisons) |
| `varchar(n)` | `CharField(max_length=n)` ; si valeurs fixes : `TextChoices` **et** `CheckConstraint` |
| `text` | `TextField` |
| `int`, `smallint` | `IntegerField`, `SmallIntegerField` (positifs : `PositiveIntegerField`) |
| `numeric(7,1)` | `DecimalField(max_digits=7, decimal_places=1)` |
| `boolean` | `BooleanField` |
| `date` / `timestamptz` | `DateField` / `DateTimeField` (`USE_TZ = True`, fuseau `Africa/Abidjan` à l'affichage, UTC en base) |
| `jsonb` | `JSONField` |
| `geography(Point,4326)` | `PointField(geography=True)` (GeoDjango) |
| `geometry(MultiPolygon,4326)` | `MultiPolygonField(srid=4326)` |
| `bigint` identité | `BigAutoField` |
| `CHECK` | `CheckConstraint` dans `Meta.constraints` (Django 5.1+ : `condition=` ; avant : `check=`) |
| `UNIQUE partiel` | `UniqueConstraint(fields=[...], condition=Q(...), name=...)` |
| `NULLS NOT DISTINCT` | `UniqueConstraint(..., nulls_distinct=False)` (Django 5.0+, PostgreSQL 15+ ; **vérifier avec `sqlmigrate`** que l'index créé contient bien `NULLS NOT DISTINCT`, y compris avec `condition`) |

**GDAL (Windows)** : si `django.contrib.gis` n'est pas utilisable, remplacer **temporairement et à l'identique pour toute l'équipe** chaque champ géographique par `latitude`/`longitude` (`DecimalField(9,6)`), après décision écrite du chef de projet. Ne jamais mélanger les deux.

**Tables de liaison à clé composée** : Django 5.2+ : `CompositePrimaryKey`. Avant 5.2 : colonne `id` technique + `UniqueConstraint` sur la paire (même garantie d'unicité). Utiliser la même méthode partout.

### 4.3 Dates
Un événement a deux dates : `occurred_at` (quand c'est arrivé, selon l'appareil) et `created_at` (quand le serveur l'a reçu). Ne jamais les confondre. Le moteur d'exposition travaille sur `occurred_at` (départ) et `movement.received_at` (réception).

## 5. Classes de base et protections

### 5.1 Code à créer dans `backend/apps/core/models.py`
```python
import uuid
from django.db import models
from django.conf import settings


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # uuid7 si disponible
    class Meta:
        abstract = True


class StateModel(UUIDModel):  # bloc ETAT
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_simulated = models.BooleanField(default=False)
    class Meta:
        abstract = True


class EventFields(UUIDModel):  # colonnes EVT, sans immuabilité
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    device = models.ForeignKey("accounts.Device", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    is_simulated = models.BooleanField(default=False)
    class Meta:
        abstract = True


class EventModel(EventFields):  # bloc EVT : ajout seul
    class Meta:
        abstract = True
    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Un événement ne se modifie pas.")
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        raise RuntimeError("Un événement ne se supprime pas.")


class DeclarationModel(EventFields):  # colonnes EVT + cache modifiable par services.py
    class Meta:
        abstract = True


class CorrectableMixin(models.Model):  # bloc COR
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    class Meta:
        abstract = True
    # Dans chaque Meta concrète : UniqueConstraint(fields=["supersedes"],
    #   condition=models.Q(supersedes__isnull=False), name="uniq_<table>_supersedes")


class PositionMixin(models.Model):  # bloc POS
    class Source(models.TextChoices):
        GPS = "gps"; NETWORK = "network"; MANUAL = "manual"; NONE = "none"
    position = models.PointField(geography=True, null=True, blank=True)
    position_accuracy_m = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    position_source = models.CharField(max_length=8, choices=Source.choices, default=Source.NONE)
    class Meta:
        abstract = True
```
**Piège** : `save()`/`delete()` ne sont pas appelés par `QuerySet.update()`, `bulk_update()`, `bulk_create` en mode mise à jour, ni par du SQL direct. Les **triggers de la section 7 sont obligatoires** : ils sont la vraie protection.

### 5.2 Quels modèles utilisent quoi
- **Événements immuables (`EventModel`)** : `movement_confirmation`, `movement_status_event`, `identity_verification`, `health_report_review`, `alert_review`, `alert_event`, `status_event`, `health_event`. Plus `audit_log` (protégé par la base).
- **Déclarations (`DeclarationModel`)** : `movement`, `health_report`, `movement_discrepancy`, `ownership_claim` : les colonnes d'origine (qui, quand, où) ne changent jamais ; seules les colonnes de cache/statut changent, via `services.py`.
- **Corrigeables (`CorrectableMixin`)** : `health_event`, `status_event`, `ownership_claim`. Une ligne ne se corrige qu'une fois.
- **Position (`PositionMixin`)** : `identity_verification`, `movement_confirmation`, `status_event`, `health_report`.

## 6. Les tables, application par application

Légende : « CALCULÉ » = cache écrit seulement par `services.py` du module. « bloc EVT / POS / ETAT / COR » : voir sections 4 et 5. Une ligne « UNIQUE partiel » = `UniqueConstraint` avec `condition`. Pour chaque table : **table SQL**, **classe Django**, **base à hériter**.


### Application `accounts`  (responsable : Chef de projet)


#### `app_user`  ->  `User`  (AbstractBaseUser + PermissionsMixin (pk uuid))

Compte de connexion (Django AbstractBaseUser). Connexion par téléphone.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK | généré côté appareil ou serveur |
| `phone` | `varchar(20)` | NOT NULL, UNIQUE | format E.164 (+225...) ; identifiant de connexion |
| `password` | `varchar(128)` | NOT NULL | hash Django, jamais en clair |
| `full_name` | `varchar(120)` | NOT NULL |  |
| `language` | `varchar(5)` | NOT NULL DEFAULT 'fr' |  |
| `is_active` | `boolean` | NOT NULL DEFAULT true | désactiver plutôt que supprimer |
| `phone_verified_at` | `timestamptz` | NULL | NULL = numéro non vérifié par code SMS |
| `is_staff` | `boolean` | NOT NULL DEFAULT false | accès /admin Django (équipe technique seulement) |
| `is_superuser` | `boolean` | NOT NULL DEFAULT false | exigé par Django (PermissionsMixin) ; réservé à l'équipe technique, jamais un rôle métier |
| `last_login` | `timestamptz` | NULL |  |
| `created_at` | `timestamptz` | NOT NULL DEFAULT now() |  |
| `is_simulated` | `boolean` | NOT NULL DEFAULT false | donnée de démonstration |

#### `organization`  ->  `Organization`  (StateModel)

Service vétérinaire, coopérative, marché, abattoir...

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `name` | `varchar(160)` | NOT NULL |  |
| `kind` | `varchar(20)` | NOT NULL, CHECK IN ('veterinary_service','cooperative','market','abattoir','authority','other') | valeurs stables |
| `zone_id` | `uuid` | FK zone NULL | rattachement géographique |
| `is_active` | `boolean` | NOT NULL DEFAULT true |  |
| `created_at, is_simulated` | `-` | bloc ETAT |  |

#### `role`  ->  `Role`  (UUIDModel)

Catalogue des rôles (table, pas enum, pour pouvoir en ajouter).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `code` | `varchar(30)` | NOT NULL, UNIQUE | breeder, field_agent, veterinarian, authority, trader... |
| `label_fr` | `varchar(80)` | NOT NULL |  |
| `description` | `text` | NULL |  |

#### `membership`  ->  `Membership`  (UUIDModel)

Un utilisateur exerce un rôle, éventuellement dans une organisation et sur une zone.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `user_id` | `uuid` | FK app_user NOT NULL |  |
| `role_id` | `uuid` | FK role NOT NULL |  |
| `organization_id` | `uuid` | FK organization NULL |  |
| `zone_id` | `uuid` | FK zone NULL | périmètre d'action |
| `starts_at` | `timestamptz` | NOT NULL |  |
| `ends_at` | `timestamptz` | NULL, CHECK ends_at > starts_at | NULL = en cours |
| `UNIQUE partiel` | `-` | (user_id, role_id, organization_id) NULLS NOT DISTINCT WHERE ends_at IS NULL | pas de doublon actif, même quand organization_id est NULL |

#### `habilitation`  ->  `Habilitation`  (StateModel)

Preuve qu'un vétérinaire (ou agent) est habilité. Condition de toute validation sanitaire.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `user_id` | `uuid` | FK app_user NOT NULL |  |
| `kind` | `varchar(20)` | NOT NULL, CHECK IN ('vet_order','mandate_state','other') |  |
| `reference_number` | `varchar(60)` | NOT NULL | n° d'ordre ou d'agrément |
| `valid_from, valid_to` | `date` | NOT NULL, CHECK valid_to >= valid_from |  |
| `status` | `varchar(12)` | NOT NULL, CHECK IN ('pending','verified','revoked','expired') |  |
| `verified_by` | `uuid` | FK app_user NULL | jamais l'intéressé lui-même (CHECK verified_by <> user_id) |
| `verified_at` | `timestamptz` | NULL |  |

#### `mandate`  ->  `Mandate`  (UUIDModel)

Mandat donnant à un agent le droit d'agir pour des centres (P1 simple, extensible).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `agent_user_id` | `uuid` | FK app_user NOT NULL |  |
| `granted_by` | `uuid` | FK app_user NOT NULL | le détenteur du centre ou l'autorité |
| `scope` | `varchar(20)` | NOT NULL, CHECK IN ('declare','move','all') | étendue des droits |
| `starts_at, ends_at` | `timestamptz` | NOT NULL / NULL |  |
| `revoked_at` | `timestamptz` | NULL |  |

#### `device`  ->  `Device`  (UUIDModel (id fourni par l'appareil))

Appareil enregistré d'un utilisateur.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK | généré à l'installation |
| `user_id` | `uuid` | FK app_user NOT NULL |  |
| `label` | `varchar(60)` | NULL |  |
| `platform` | `varchar(10)` | NOT NULL, CHECK IN ('android','ios','web','other') |  |
| `registered_at` | `timestamptz` | NOT NULL |  |
| `last_seen_at` | `timestamptz` | NULL |  |
| `revoked_at` | `timestamptz` | NULL | appareil perdu : accès coupé |

### Application `geo`  (responsable : Yéo)


#### `zone`  ->  `Zone`  (UUIDModel)

Découpage administratif hiérarchique (région > département > sous-préfecture...).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `parent_id` | `uuid` | FK zone NULL | hiérarchie ; racine = NULL |
| `level` | `smallint` | NOT NULL, CHECK BETWEEN 0 AND 6 | 0 = pays, 1 = région |
| `code` | `varchar(20)` | NOT NULL, UNIQUE | code officiel si connu |
| `name` | `varchar(120)` | NOT NULL |  |
| `boundary` | `geometry(MultiPolygon,4326)` | NULL | index GIST ; NULL tant que le tracé n'est pas chargé |
| `centroid` | `geography(Point,4326)` | NULL | pour les cartes agrégées |

#### `zone_stat`  ->  `ZoneStat`  (UUIDModel)

État courant d'une zone sur la carte (cache recalculé).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `zone_id` | `uuid` | FK zone NOT NULL |  |
| `species_id` | `uuid` | FK species NULL | NULL = toutes espèces |
| `state` | `varchar(10)` | NOT NULL, CHECK IN ('normal','watch','exposure','alert','unknown') | les 5 états de la charte |
| `centers_count` | `int` | NOT NULL DEFAULT 0 |  |
| `animals_count` | `int` | NOT NULL DEFAULT 0 |  |
| `is_masked` | `boolean` | NOT NULL DEFAULT false | true si effectif sous le minimum (RG anonymat) |
| `computed_at` | `timestamptz` | NOT NULL |  |
| `UNIQUE` | `-` | (zone_id, species_id) NULLS NOT DISTINCT | une ligne courante par zone et espèce (species_id NULL compte comme une valeur) |

### Application `core`  (responsable : Chef de projet)


#### `species`  ->  `Species`  (UUIDModel)

Catalogue des espèces.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `code` | `varchar(20)` | NOT NULL, UNIQUE | cattle, sheep, goat, pig, poultry... |
| `label_fr` | `varchar(60)` | NOT NULL |  |
| `tracking_mode` | `varchar(10)` | NOT NULL, CHECK IN ('animal','lot','both') | bovins = animal ; volaille = lot |
| `is_active` | `boolean` | NOT NULL DEFAULT true |  |

### Application `identity`  (responsable : Chef de projet)


#### `center`  ->  `Center`  (StateModel)

Centre d'élevage (élevage, parc, marché, abattoir...).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `name` | `varchar(160)` | NOT NULL |  |
| `organization_id` | `uuid` | FK organization NULL |  |
| `zone_id` | `uuid` | FK zone NOT NULL |  |
| `location` | `geography(Point,4326)` | NULL | index GIST |
| `location_accuracy_m` | `numeric(7,1)` | NULL |  |
| `location_source` | `varchar(10)` | NOT NULL, CHECK IN ('gps','manual','none') |  |
| `center_type` | `varchar(15)` | NOT NULL, CHECK IN ('farm','market','slaughterhouse','checkpoint','other') |  |
| `status` | `varchar(10)` | NOT NULL DEFAULT 'active', CHECK IN ('active','closed') |  |
| `created_at, created_by, is_simulated` | `-` | bloc ETAT |  |

#### `center_member`  ->  `CenterMember`  (UUIDModel)

Qui a accès à un centre. Source unique du détenteur (plusieurs personnes possibles).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `center_id` | `uuid` | FK center NOT NULL |  |
| `user_id` | `uuid` | FK app_user NOT NULL |  |
| `member_role` | `varchar(10)` | NOT NULL, CHECK IN ('holder','co_holder','worker') | holder = détenteur responsable |
| `starts_at` | `timestamptz` | NOT NULL |  |
| `ends_at` | `timestamptz` | NULL, CHECK ends_at > starts_at | NULL = en cours |
| `UNIQUE partiel 1` | `-` | (center_id) WHERE member_role='holder' AND ends_at IS NULL | exactement un détenteur actif par centre |
| `UNIQUE partiel 2` | `-` | (center_id, user_id) WHERE ends_at IS NULL | pas de doublon actif |

#### `center_species`  ->  `CenterSpecies`  (liaison)

Espèces élevées dans un centre.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `center_id` | `uuid` | FK center NOT NULL | PK composite (center_id, species_id) |
| `species_id` | `uuid` | FK species NOT NULL |  |

#### `tracked_unit`  ->  `TrackedUnit`  (StateModel)

SUPERTYPE : tout ce qui est suivi (animal ou lot). Toutes les autres tables pointent ici.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK | identifiant unique, jamais réutilisé |
| `kind` | `varchar(6)` | NOT NULL, CHECK IN ('animal','lot') | discriminant, non modifiable |
| `species_id` | `uuid` | FK species NOT NULL |  |
| `current_center_id` | `uuid` | FK center NULL | CHAMP CALCULÉ : écrit seulement par services.py de traceability |
| `life_status` | `varchar(10)` | NOT NULL DEFAULT 'active', CHECK IN ('active','dead','slaughtered','missing','closed') | CALCULÉ à partir de status_event |
| `local_name` | `varchar(60)` | NULL | nom donné par l'éleveur (facultatif) |
| `merged_into_id` | `uuid` | FK tracked_unit NULL | doublon fusionné (P2) |
| `origin_unit_id` | `uuid` | FK tracked_unit NULL | lignée : lot créé par fractionnement d'un autre lot (voir movement_item.received_unit_id) |
| `created_at, created_by, device_id, is_simulated` | `-` | bloc ETAT |  |

#### `animal`  ->  `Animal`  (1-1 (pk = unit))

SOUS-TYPE individuel (1 ligne par tracked_unit de kind 'animal').

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `unit_id` | `uuid` | PK, FK tracked_unit | PK = FK (1-1) |
| `sex` | `varchar(7)` | NOT NULL DEFAULT 'unknown', CHECK IN ('male','female','unknown') |  |
| `birth_date` | `date` | NULL |  |
| `birth_date_precision` | `varchar(9)` | NULL, CHECK IN ('day','month','year','estimated') |  |
| `breed` | `varchar(60)` | NULL | texte libre en P1 |
| `marks` | `text` | NULL | signes particuliers |
| `mother_unit_id` | `uuid` | FK animal NULL | filiation (P2) |

#### `lot`  ->  `Lot`  (1-1 (pk = unit))

SOUS-TYPE collectif (volaille, petits ruminants en groupe).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `unit_id` | `uuid` | PK, FK tracked_unit | PK = FK (1-1) |
| `current_size` | `int` | NOT NULL, CHECK > 0 | CALCULÉ ; chaque changement écrit un status_event 'size_change' |
| `description` | `varchar(120)` | NULL |  |

#### `label_batch`  ->  `LabelBatch`  (UUIDModel)

Lot d'impression d'étiquettes numérotées.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `quantity` | `int` | NOT NULL, CHECK > 0 |  |
| `created_by` | `uuid` | FK app_user NOT NULL |  |
| `created_at` | `timestamptz` | NOT NULL DEFAULT now() |  |
| `note` | `varchar(160)` | NULL |  |

#### `label`  ->  `Label`  (UUIDModel)

Une étiquette physique pré-numérotée. Le QR contient uniquement short_code.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `batch_id` | `uuid` | FK label_batch NOT NULL |  |
| `short_code` | `char(9)` | NOT NULL, UNIQUE, CHECK ~ '^[2-9A-HJ-NP-Z]{9}$' | 8 caractères lisibles + 1 caractère de contrôle (calculé par l'application) ; sans 0, O, 1, I |
| `kind` | `varchar(10)` | NOT NULL DEFAULT 'qr', CHECK IN ('qr','ear_tag','other') |  |
| `status` | `varchar(12)` | NOT NULL DEFAULT 'printed', CHECK IN ('printed','issued','active','deactivated','lost') |  |
| `issued_to_center_id` | `uuid` | FK center NULL | centre à qui elle a été remise |

#### `identity_support`  ->  `IdentitySupport`  (UUIDModel)

Association unité <-> support d'identité (étiquette, marque visible, puce plus tard). Historisée.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `support_type` | `varchar(12)` | NOT NULL, CHECK IN ('qr_label','visible_mark','rfid_future') |  |
| `label_id` | `uuid` | FK label NULL | obligatoire si qr_label (CHECK) |
| `mark_text` | `varchar(60)` | NULL | description d'une marque visible |
| `bound_at` | `timestamptz` | NOT NULL |  |
| `bound_by` | `uuid` | FK app_user NOT NULL |  |
| `unbound_at` | `timestamptz` | NULL |  |
| `unbound_reason` | `varchar(10)` | NULL, CHECK IN ('lost','damaged','replaced','error') |  |
| `UNIQUE partiel 1` | `-` | (label_id) WHERE unbound_at IS NULL | une étiquette = une unité active |
| `UNIQUE partiel 2` | `-` | (unit_id) WHERE support_type='qr_label' AND unbound_at IS NULL | une unité = une étiquette QR active |

#### `identity_verification`  ->  `IdentityVerification`  (EventModel + PositionMixin)

Contrôle d'identité à un scan (EVT, append-only).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `label_id` | `uuid` | FK label NULL |  |
| `method` | `varchar(12)` | NOT NULL, CHECK IN ('scan','manual_code','photo_compare') |  |
| `result` | `varchar(10)` | NOT NULL, CHECK IN ('confirmed','mismatch','unreadable') |  |
| `(bloc EVT)` | `-` | voir sections 4 et 5 |  |
| `(bloc POS)` | `-` | voir sections 4 et 5 | position uniquement à l'instant du scan |

#### `ownership_claim`  ->  `OwnershipClaim`  (DeclarationModel + CorrectableMixin)

Propriétaire ou détenteur déclaré. Historique conservé, jamais écrasé.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `party_user_id` | `uuid` | FK app_user NOT NULL |  |
| `role` | `varchar(10)` | NOT NULL, CHECK IN ('owner','holder') | propriétaire déclaré / détenteur |
| `status` | `varchar(10)` | NOT NULL DEFAULT 'declared', CHECK IN ('declared','contested','confirmed','superseded') | aucune valeur légale |
| `starts_at, ends_at` | `timestamptz` | NOT NULL / NULL |  |
| `(colonnes EVT)` | `-` | voir sections 4 et 5 |  |
| `(bloc COR)` | `-` | voir sections 4 et 5 | UNIQUE partiel (supersedes_id) : une correction par ligne |

#### `subject_photo`  ->  `SubjectPhoto`  (UUIDModel)

Photos d'une unité.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `attachment_id` | `uuid` | FK attachment NOT NULL |  |
| `purpose` | `varchar(12)` | NOT NULL, CHECK IN ('registration','health','verification') |  |
| `taken_at` | `timestamptz` | NOT NULL |  |
| `created_by` | `uuid` | FK app_user NOT NULL |  |

#### `mandate_center`  ->  `MandateCenter`  (liaison)

Association mandat <-> centre.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `mandate_id` | `uuid` | FK mandate NOT NULL | PK composite (mandate_id, center_id) |
| `center_id` | `uuid` | FK center NOT NULL |  |

#### `attachment`  ->  `Attachment`  (UUIDModel)

Fichier (photo, pièce jointe). Le fichier est sur disque/stockage, la base garde la référence.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `storage_key` | `varchar(255)` | NOT NULL, UNIQUE | chemin ou clé de stockage |
| `mime_type` | `varchar(80)` | NOT NULL |  |
| `size_bytes` | `int` | NOT NULL, CHECK > 0 |  |
| `sha256` | `char(64)` | NOT NULL | détection de doublon et d'altération |
| `uploaded_by` | `uuid` | FK app_user NOT NULL |  |
| `created_at` | `timestamptz` | NOT NULL DEFAULT now() |  |

### Application `traceability`  (responsable : Konan Romuald)


#### `movement`  ->  `Movement`  (DeclarationModel)

Déclaration de mouvement (sortie d'un centre, vers un autre). Le statut est un cache du dernier movement_status_event.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK | généré par l'appareil |
| `movement_type` | `varchar(10)` | NOT NULL, CHECK IN ('transfer','sale','slaughter','temporary','return') | temporary/return = P2 |
| `from_center_id` | `uuid` | FK center NOT NULL |  |
| `to_center_id` | `uuid` | FK center NULL | NULL si destination non enregistrée |
| `to_party_note` | `varchar(160)` | NULL | destinataire en texte si hors système |
| `status` | `varchar(14)` | NOT NULL, CHECK IN ('declared','confirmed','partial','disputed','cancelled','expired') | CALCULÉ (cache) |
| `expected_return_on` | `date` | NULL | transhumance (P2) |
| `planned_route` | `jsonb` | NULL | itinéraire prévu facultatif (P2) |
| `CHECK` | `-` | from_center_id <> to_center_id |  |
| `received_at` | `timestamptz` | NULL | CALCULÉ : date de réception confirmée (sert aux fenêtres du moteur d'exposition) |
| `(colonnes EVT)` | `-` | voir sections 4 et 5 | occurred_at = date du départ ; table modifiable par services.py (status, received_at) |

#### `movement_item`  ->  `MovementItem`  (liaison)

Association mouvement <-> unité, avec quantités.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `movement_id` | `uuid` | FK movement NOT NULL | PK composite (movement_id, unit_id) |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `quantity_sent` | `int` | NOT NULL DEFAULT 1, CHECK > 0 | =1 pour un animal (contrôlé par la couche service) |
| `quantity_received` | `int` | NULL, CHECK >= 0 | renseigné à la réception |
| `received_unit_id` | `uuid` | FK tracked_unit NULL | unité qui existe chez le destinataire : la même si tout part, sinon le NOUVEAU lot créé par fractionnement (origin_unit_id) |

#### `unit_open_movement`  ->  `UnitOpenMovement`  (pk = unit_id (verrou))

Verrou : une unité ne peut être que dans UN mouvement non terminé. Ligne créée à la déclaration, supprimée à la clôture (seule table métier à suppression physique).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `unit_id` | `uuid` | PK, FK tracked_unit | PK = au plus un mouvement ouvert par unité (empêche de vendre deux fois le même animal) |
| `movement_id` | `uuid` | FK movement NOT NULL |  |
| `since` | `timestamptz` | NOT NULL DEFAULT now() |  |

#### `movement_confirmation`  ->  `MovementConfirmation`  (EventModel + PositionMixin)

Double confirmation : expéditeur puis destinataire (EVT).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `movement_id` | `uuid` | FK movement NOT NULL |  |
| `side` | `varchar(8)` | NOT NULL, CHECK IN ('sender','receiver') |  |
| `decision` | `varchar(24)` | NOT NULL, CHECK IN ('confirm','refuse','confirm_with_discrepancy') |  |
| `UNIQUE` | `-` | (movement_id, side) | une confirmation par côté |
| `(bloc EVT)` | `-` | voir sections 4 et 5 |  |
| `(bloc POS)` | `-` | voir sections 4 et 5 |  |

#### `movement_confirmation_code`  ->  `MovementConfirmationCode`  (UUIDModel)

Code à usage unique que le destinataire saisit pour confirmer.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `movement_id` | `uuid` | FK movement NOT NULL |  |
| `code_hash` | `varchar(128)` | NOT NULL | le code n'est jamais stocké en clair |
| `expires_at` | `timestamptz` | NOT NULL |  |
| `used_at` | `timestamptz` | NULL |  |
| `attempts` | `smallint` | NOT NULL DEFAULT 0, CHECK <= 5 | limite anti-devinette |

#### `movement_discrepancy`  ->  `MovementDiscrepancy`  (DeclarationModel)

Écart constaté au rapprochement (manquant, en trop...).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `movement_id` | `uuid` | FK movement NOT NULL |  |
| `unit_id` | `uuid` | FK tracked_unit NULL |  |
| `kind` | `varchar(18)` | NOT NULL, CHECK IN ('missing','extra','count_mismatch','identity_mismatch') |  |
| `quantity_expected, quantity_found` | `int` | NULL |  |
| `status` | `varchar(8)` | NOT NULL DEFAULT 'open', CHECK IN ('open','resolved') |  |
| `resolved_by, resolved_at, resolution_note` | `-` | NULL |  |
| `(colonnes EVT)` | `-` | voir sections 4 et 5 |  |

#### `movement_status_event`  ->  `MovementStatusEvent`  (EventModel)

Journal des changements de statut d'un mouvement (EVT, append-only).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `movement_id` | `uuid` | FK movement NOT NULL |  |
| `status` | `varchar(14)` | NOT NULL | mêmes valeurs que movement.status |
| `reason` | `varchar(160)` | NULL |  |
| `(bloc EVT)` | `-` | voir sections 4 et 5 |  |

#### `status_event`  ->  `StatusEvent`  (EventModel + CorrectableMixin + PositionMixin)

Événements de vie d'une unité : naissance, décès, abattage, disparition, vol déclaré...

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `event_type` | `varchar(16)` | NOT NULL, CHECK IN ('birth','death','slaughter','missing','found','size_change','stolen_declared','stolen_lifted','merge') |  |
| `payload` | `jsonb` | NOT NULL DEFAULT '{}' | détails propres au type (ex : ancien et nouvel effectif) |
| `visibility` | `varchar(14)` | NOT NULL DEFAULT 'owner', CHECK IN ('owner','professionals','all') | vol : professionnels habilités seulement |
| `(bloc EVT)` | `-` | voir sections 4 et 5 |  |
| `(bloc POS)` | `-` | voir sections 4 et 5 |  |
| `(bloc COR)` | `-` | voir sections 4 et 5 | UNIQUE partiel (supersedes_id) : une correction par ligne |

### Application `health`  (responsable : Yéo)


#### `disease`  ->  `Disease`  (UUIDModel)

Catalogue des maladies.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `code` | `varchar(30)` | NOT NULL, UNIQUE |  |
| `label_fr` | `varchar(100)` | NOT NULL |  |
| `is_notifiable` | `boolean` | NOT NULL DEFAULT false |  |
| `is_active` | `boolean` | NOT NULL DEFAULT true |  |

#### `disease_species`  ->  `DiseaseSpecies`  (liaison)

Espèces concernées par une maladie.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `disease_id` | `uuid` | FK disease NOT NULL | PK composite (disease_id, species_id) |
| `species_id` | `uuid` | FK species NOT NULL |  |

#### `symptom`  ->  `Symptom`  (UUIDModel)

Catalogue des symptômes (formulation simple, pictogramme).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `code` | `varchar(30)` | NOT NULL, UNIQUE |  |
| `label_fr` | `varchar(100)` | NOT NULL | vocabulaire simple de la charte |
| `icon` | `varchar(40)` | NULL | nom d'icône |
| `is_active` | `boolean` | NOT NULL DEFAULT true |  |

#### `symptom_species`  ->  `SymptomSpecies`  (liaison)

Symptômes proposés selon l'espèce.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `symptom_id` | `uuid` | FK symptom NOT NULL | PK composite (symptom_id, species_id) |
| `species_id` | `uuid` | FK species NOT NULL |  |

#### `health_event`  ->  `HealthEvent`  (EventModel + CorrectableMixin)

Carnet sanitaire d'une unité : vaccination, traitement, examen (EVT).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `event_type` | `varchar(14)` | NOT NULL, CHECK IN ('vaccination','treatment','examination','lab_result') | lab_result = P2 |
| `disease_id` | `uuid` | FK disease NULL |  |
| `product` | `varchar(80)` | NULL |  |
| `notes` | `text` | NULL |  |
| `(bloc EVT)` | `-` | voir sections 4 et 5 |  |
| `(bloc COR)` | `-` | voir sections 4 et 5 | UNIQUE partiel (supersedes_id) : une correction par ligne |

#### `health_report`  ->  `HealthReport`  (DeclarationModel + PositionMixin)

Signalement sanitaire d'un éleveur ou agent. Le statut est un cache de health_report_review.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK | généré par l'appareil |
| `center_id` | `uuid` | FK center NOT NULL |  |
| `report_kind` | `varchar(18)` | NOT NULL, CHECK IN ('suspicion','death','abnormal_mortality') |  |
| `affected_count` | `int` | NOT NULL DEFAULT 1, CHECK > 0 |  |
| `self_severity` | `varchar(6)` | NOT NULL, CHECK IN ('low','medium','high') | gravité estimée par l'éleveur |
| `note` | `varchar(500)` | NULL | texte court |
| `status` | `varchar(12)` | NOT NULL DEFAULT 'submitted', CHECK IN ('submitted','under_review','validated','rejected','closed') | CALCULÉ (cache) |
| `(colonnes EVT)` | `-` | voir sections 4 et 5 | occurred_at = date d'observation |
| `(bloc POS)` | `-` | voir sections 4 et 5 |  |

#### `health_report_symptom`  ->  `HealthReportSymptom`  (liaison)

Symptômes cochés dans un signalement.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `report_id` | `uuid` | FK health_report NOT NULL | PK composite (report_id, symptom_id) |
| `symptom_id` | `uuid` | FK symptom NOT NULL |  |

#### `health_report_subject`  ->  `HealthReportSubject`  (liaison)

Animaux ou lots concernés par un signalement.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `report_id` | `uuid` | FK health_report NOT NULL | PK composite (report_id, unit_id) |
| `unit_id` | `uuid` | FK tracked_unit NOT NULL |  |
| `condition` | `varchar(10)` | NOT NULL, CHECK IN ('sick','dead','suspect','contact') |  |
| `notes` | `varchar(200)` | NULL |  |

#### `health_report_attachment`  ->  `HealthReportAttachment`  (liaison)

Photos jointes.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `report_id` | `uuid` | FK health_report NOT NULL | PK composite (report_id, attachment_id) |
| `attachment_id` | `uuid` | FK attachment NOT NULL |  |

#### `health_report_review`  ->  `HealthReportReview`  (EventModel)

Évaluation d'un signalement par un vétérinaire habilité (EVT, append-only).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `report_id` | `uuid` | FK health_report NOT NULL |  |
| `decision` | `varchar(20)` | NOT NULL, CHECK IN ('request_info','retain_suspicion','raise_level2','validate_level3','dismiss','close') |  |
| `disease_id` | `uuid` | FK disease NULL | maladie retenue |
| `habilitation_id` | `uuid` | FK habilitation NOT NULL | preuve d'habilitation valide au moment de la décision |
| `note` | `text` | NULL |  |
| `(bloc EVT)` | `-` | voir sections 4 et 5 |  |

### Application `alerts`  (responsable : Yéo)


#### `disease_rule`  ->  `DiseaseRule`  (UUIDModel (immuable une fois utilisée))

Règle sanitaire VERSIONNÉE. Valeurs jamais écrites dans le code.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `disease_id` | `uuid` | FK disease NOT NULL |  |
| `species_id` | `uuid` | FK species NULL | NULL = toutes espèces |
| `version` | `int` | NOT NULL, CHECK > 0 |  |
| `lookback_days` | `int` | NOT NULL, CHECK >= 0 | période d'exposition en amont |
| `lookforward_days` | `int` | NOT NULL, CHECK >= 0 | période en aval |
| `max_depth` | `smallint` | NOT NULL, CHECK BETWEEN 1 AND 6 | profondeur de propagation |
| `min_zone_effectif` | `int` | NOT NULL DEFAULT 5, CHECK >= 1 | seuil d'affichage carte |
| `valid_from, valid_to` | `date` | NOT NULL / NULL |  |
| `approved_by` | `uuid` | FK app_user NOT NULL |  |
| `include_unconfirmed` | `boolean` | NOT NULL DEFAULT true | true = un mouvement déclaré mais non confirmé compte (prudence) |
| `cluster_window_days` | `int` | NOT NULL DEFAULT 7, CHECK > 0 | regroupement de zone : fenêtre glissante (en jours) sur `health_report.occurred_at` |
| `cluster_min_reports` | `smallint` | NOT NULL DEFAULT 3, CHECK >= 2 | regroupement de zone : nombre minimal de signalements compatibles |
| `cluster_min_ratio` | `numeric(5,4)` | NULL, CHECK (cluster_min_ratio > 0 AND cluster_min_ratio <= 1) | part minimale d'animaux touchés rapportée à l'effectif connu des centres concernés ; NULL = non utilisé |
| `escalation_hours` | `int` | NOT NULL DEFAULT 24, CHECK > 0 | délai sans réponse d'un vétérinaire avant relance / escalade |
| `UNIQUE` | `-` | (disease_id, species_id, version) NULLS NOT DISTINCT | une règle utilisée n'est jamais modifiée : on crée la version suivante |

Les valeurs par défaut des colonnes `cluster_*` et `escalation_hours` sont **expérimentales**, pour la démonstration : elles doivent être validées par un vétérinaire avant tout usage réel.

#### `alert`  ->  `Alert`  (StateModel)

Alerte sanitaire. Niveau 3 = validée par un vétérinaire habilité.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `disease_id` | `uuid` | FK disease NULL | NULL tant que non retenue |
| `rule_id` | `uuid` | FK disease_rule NOT NULL | règle appliquée (traçabilité du calcul) |
| `trigger_kind` | `varchar(14)` | NOT NULL DEFAULT 'single_report', CHECK IN ('single_report','zone_cluster') | origine : un signalement évalué, ou un regroupement de signalements dans une zone (section 9.9) |
| `focus_center_id` | `uuid` | FK center NULL, CHECK (trigger_kind = 'zone_cluster' OR focus_center_id IS NOT NULL) | foyer ; NULL seulement pour une alerte de zone, dont les centres de départ sont ceux des signalements regroupés (`alert_report` -> `health_report.center_id`) |
| `zone_id` | `uuid` | FK zone NOT NULL |  |
| `species_id` | `uuid` | FK species NULL, CHECK (trigger_kind <> 'zone_cluster' OR species_id IS NOT NULL) | espèce du regroupement ; obligatoire pour une alerte de zone |
| `confidence` | `varchar(7)` | NOT NULL DEFAULT 'normal', CHECK IN ('normal','reduced') | `reduced` si l'effectif d'au moins un centre concerné est inconnu ; affiché au vétérinaire |
| `escalation_due_at` | `timestamptz` | NULL | CALCULÉ : échéance de relance si aucun vétérinaire n'a répondu ; NULL = pas de relance en attente |
| `level` | `smallint` | NOT NULL, CHECK IN (1,2,3) |  |
| `status` | `varchar(10)` | NOT NULL DEFAULT 'open', CHECK IN ('open','monitoring','closed','cancelled') |  |
| `opened_at` | `timestamptz` | NOT NULL |  |
| `closed_at` | `timestamptz` | NULL |  |
| `validated_by` | `uuid` | FK app_user NULL |  |
| `habilitation_id` | `uuid` | FK habilitation NULL |  |
| `validated_at` | `timestamptz` | NULL |  |
| `current_run_id` | `uuid` | NULL | calcul d'exposition en vigueur (les lignes alert_exposure portent run_id) |
| `CHECK niveau 3` | `-` | level < 3 OR (validated_by IS NOT NULL AND validated_at IS NOT NULL AND habilitation_id IS NOT NULL) | règle clé : seul un vétérinaire habilité valide |
| `created_at, is_simulated` | `-` | bloc ETAT |  |

#### `alert_report`  ->  `AlertReport`  (liaison)

Signalements regroupés dans une alerte.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `alert_id` | `uuid` | FK alert NOT NULL | PK composite (alert_id, report_id) |
| `report_id` | `uuid` | FK health_report NOT NULL |  |

#### `alert_review`  ->  `AlertReview`  (EventModel)

Décision d'un vétérinaire habilité sur une alerte, notamment une alerte de zone : confirmer, infirmer ou demander des informations (EVT, append-only).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `alert_id` | `uuid` | FK alert NOT NULL |  |
| `decision` | `varchar(10)` | NOT NULL, CHECK IN ('confirm','dismiss','need_info') | confirm = niveau 3 ; dismiss = alerte infirmée ; need_info = reste ouverte |
| `habilitation_id` | `uuid` | FK habilitation NOT NULL | preuve d'habilitation valide au moment de la décision (vérifiée par le service) |
| `note` | `text` | NULL | motif, obligatoire côté service pour `dismiss` |
| `(bloc EVT)` | `-` | voir sections 4 et 5 | `created_by` = le vétérinaire qui décide |

#### `alert_exposure`  ->  `AlertExposure`  (UUIDModel)

Résultat du calcul : centre ou unité EXPOSÉ (jamais 'contaminé'), ou exclu (cas négatif).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `alert_id` | `uuid` | FK alert NOT NULL |  |
| `run_id` | `uuid` | NOT NULL | identifie un calcul ; on garde les précédents ; le courant = alert.current_run_id |
| `center_id` | `uuid` | FK center NOT NULL |  |
| `unit_id` | `uuid` | FK tracked_unit NULL |  |
| `exposure_status` | `varchar(18)` | NOT NULL, CHECK IN ('exposed','excluded_negative','monitoring','cleared') | le cas négatif est stocké et expliqué |
| `depth` | `smallint` | NOT NULL, CHECK >= 0 |  |
| `last_contact_at` | `timestamptz` | NULL |  |
| `computed_at` | `timestamptz` | NOT NULL |  |
| `UNIQUE` | `-` | (alert_id, run_id, center_id, unit_id) NULLS NOT DISTINCT | PostgreSQL 15+ ; sans cela deux lignes avec unit_id NULL seraient acceptées |

#### `alert_exposure_step`  ->  `AlertExposureStep`  (UUIDModel)

Chemin explicable : chaque étape du lien entre le foyer et l'exposé.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `exposure_id` | `uuid` | FK alert_exposure NOT NULL |  |
| `step_no` | `smallint` | NOT NULL, CHECK >= 1 |  |
| `movement_id` | `uuid` | FK movement NULL |  |
| `from_center_id, to_center_id` | `uuid` | FK center NOT NULL |  |
| `unit_id` | `uuid` | FK tracked_unit NULL |  |
| `occurred_at` | `timestamptz` | NOT NULL |  |
| `explanation_code` | `varchar(30)` | NOT NULL | ex : sent_from_focus, received_in_window, outside_window |
| `UNIQUE` | `-` | (exposure_id, step_no) |  |

#### `alert_event`  ->  `AlertEvent`  (EventModel)

Journal de l'alerte : changement de niveau, notification, clôture (EVT).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `alert_id` | `uuid` | FK alert NOT NULL |  |
| `event_type` | `varchar(16)` | NOT NULL, CHECK IN ('opened','level_changed','recomputed','notified','vets_notified','escalated','reviewed','reopened','closed','cancelled') | longueur maximale 13 (`level_changed`, `vets_notified`) : `varchar(16)` suffit |
| `payload` | `jsonb` | NOT NULL DEFAULT '{}' |  |
| `(bloc EVT)` | `-` | voir sections 4 et 5 |  |

#### `investigation`  ->  `Investigation`  (StateModel (P2))

Enquête de terrain (P2).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `alert_id` | `uuid` | FK alert NOT NULL |  |
| `center_id` | `uuid` | FK center NOT NULL |  |
| `assigned_to` | `uuid` | FK app_user NOT NULL |  |
| `status` | `varchar(10)` | NOT NULL DEFAULT 'open', CHECK IN ('open','done','cancelled') |  |
| `findings` | `text` | NULL |  |
| `opened_at, closed_at` | `timestamptz` | NOT NULL / NULL |  |

#### `quarantine`  ->  `Quarantine`  (StateModel (P2))

Restriction de mouvement (P2).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `alert_id` | `uuid` | FK alert NOT NULL |  |
| `center_id` | `uuid` | FK center NULL |  |
| `unit_id` | `uuid` | FK tracked_unit NULL |  |
| `CHECK` | `-` | center_id IS NOT NULL OR unit_id IS NOT NULL |  |
| `starts_on, ends_on` | `date` | NOT NULL / NULL |  |
| `ordered_by` | `uuid` | FK app_user NOT NULL | vétérinaire habilité |
| `habilitation_id` | `uuid` | FK habilitation NOT NULL |  |

### Application `sync`  (responsable : Konan Romuald)


#### `sync_operation`  ->  `SyncOperation`  (UUIDModel (id fourni par l'appareil, sans default))

File d'envoi côté serveur. L'identifiant généré par l'appareil sert de clé d'idempotence.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK | UUID de l'opération créé HORS LIGNE ; rejouer = sans effet |
| `device_id` | `uuid` | FK device NOT NULL |  |
| `user_id` | `uuid` | FK app_user NOT NULL |  |
| `server_seq` | `bigint` | NOT NULL, UNIQUE, IDENTITY | ordre d'arrivée sur le serveur |
| `op_type` | `varchar(40)` | NOT NULL | ex : movement.declare |
| `payload` | `jsonb` | NOT NULL |  |
| `client_created_at` | `timestamptz` | NOT NULL |  |
| `received_at` | `timestamptz` | NOT NULL DEFAULT now() |  |
| `status` | `varchar(10)` | NOT NULL DEFAULT 'pending', CHECK IN ('pending','applied','rejected','conflict') |  |
| `error_code` | `varchar(40)` | NULL |  |
| `applied_at` | `timestamptz` | NULL |  |

#### `sync_conflict`  ->  `SyncConflict`  (UUIDModel)

Conflit détecté à l'application d'une opération.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `operation_id` | `uuid` | FK sync_operation NOT NULL |  |
| `kind` | `varchar(30)` | NOT NULL | ex : unit_already_moved |
| `detail` | `jsonb` | NOT NULL |  |
| `status` | `varchar(8)` | NOT NULL DEFAULT 'open', CHECK IN ('open','resolved') |  |
| `resolved_by, resolved_at, resolution` | `-` | NULL |  |

#### `change_feed`  ->  `ChangeFeed`  (BigAutoField (seq))

Flux des changements que les appareils récupèrent depuis leur dernier curseur.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `seq` | `bigint` | PK, IDENTITY | le curseur du client |
| `entity_table` | `varchar(40)` | NOT NULL |  |
| `entity_id` | `uuid` | NOT NULL |  |
| `change` | `varchar(6)` | NOT NULL, CHECK IN ('insert','update') |  |
| `center_id` | `uuid` | FK center NULL | portée de visibilité |
| `zone_id` | `uuid` | FK zone NULL |  |
| `created_at` | `timestamptz` | NOT NULL DEFAULT now() |  |

### Application `notifications`  (responsable : Chef de projet)


#### `notification`  ->  `Notification`  (UUIDModel)

Message neutre envoyé à un utilisateur (jamais l'identité de l'élevage d'origine).

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `uuid` | PK |  |
| `user_id` | `uuid` | FK app_user NOT NULL |  |
| `alert_id` | `uuid` | FK alert NULL |  |
| `kind` | `varchar(24)` | NOT NULL |  |
| `message_code` | `varchar(40)` | NOT NULL | gabarit de message du vocabulaire officiel |
| `params` | `jsonb` | NOT NULL DEFAULT '{}' |  |
| `channel` | `varchar(8)` | NOT NULL, CHECK IN ('in_app','sms','push') |  |
| `status` | `varchar(8)` | NOT NULL DEFAULT 'pending', CHECK IN ('pending','sent','read','failed') |  |
| `dedup_key` | `varchar(80)` | NULL, UNIQUE | évite d'envoyer deux fois la même chose |
| `created_at, sent_at, read_at` | `timestamptz` | NOT NULL / NULL / NULL |  |

### Application `audit`  (responsable : Chef de projet)


#### `audit_log`  ->  `AuditLog`  (BigAutoField)

Journal inaltérable : qui a fait quoi, quand. Aucune modification ni suppression possible.

| Colonne | Type | Contraintes | Remarque |
|---|---|---|---|
| `id` | `bigint` | PK, IDENTITY |  |
| `at` | `timestamptz` | NOT NULL DEFAULT now() |  |
| `actor_user_id` | `uuid` | FK app_user NULL | NULL = système |
| `device_id` | `uuid` | FK device NULL |  |
| `action` | `varchar(40)` | NOT NULL | ex : alert.validate, movement.confirm, habilitation.verify |
| `entity_table` | `varchar(40)` | NOT NULL |  |
| `entity_id` | `uuid` | NULL |  |
| `details` | `jsonb` | NOT NULL DEFAULT '{}' | jamais de secret ni de mot de passe |
| `prev_hash, hash` | `char(64)` | NULL | chaînage facultatif (détection d'altération) |
| `Protection` | `-` | REVOKE UPDATE, DELETE + trigger de refus | ajout seul |

## 7. Triggers et SQL à écrire (migrations `RunSQL`)

Placer dans une migration nommée `NNNN_protections.py` de **l'application propriétaire de la table**.

### 7.1 Ajout seul (à appliquer sur chaque table d'événement de la section 5.2)
```sql
CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table % en ajout seul : % interdit', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_<table>_append_only
BEFORE UPDATE OR DELETE ON <table>
FOR EACH ROW EXECUTE FUNCTION forbid_update_delete();
```
`audit_log` : en plus `REVOKE UPDATE, DELETE ON audit_log FROM <role_applicatif>;`. Prévoir `TRUNCATE` interdit pour le rôle applicatif.

### 7.2 Sous-type cohérent
`animal.unit_id` doit pointer un `tracked_unit` de `kind='animal'` ; `lot.unit_id`, `kind='lot'`. Trigger `BEFORE INSERT` qui lève une erreur sinon. `tracked_unit.kind` ne change jamais (trigger `BEFORE UPDATE` si `NEW.kind <> OLD.kind`).

### 7.3 Quantité d'un animal
`movement_item` : trigger `BEFORE INSERT OR UPDATE` : si l'unité est un animal, `quantity_sent = 1` et `quantity_received IN (0,1)`.

### 7.4 Règle sanitaire figée
`disease_rule` : trigger `BEFORE UPDATE` qui lève une erreur si une ligne `alert` référence déjà cette règle (`alert.rule_id`). Pour changer une règle : insérer la version suivante.

### 7.5 Autres contraintes (à écrire en `CheckConstraint` / `UniqueConstraint`, pas en trigger)
- `alert` : `level IN (1,2,3)` ; `level < 3 OR (validated_by IS NOT NULL AND validated_at IS NOT NULL AND habilitation_id IS NOT NULL)` ; `trigger_kind IN ('single_report','zone_cluster')` ; `trigger_kind = 'zone_cluster' OR focus_center_id IS NOT NULL` ; `trigger_kind <> 'zone_cluster' OR species_id IS NOT NULL` ; `confidence IN ('normal','reduced')`.
- `alert_review` : `decision IN ('confirm','dismiss','need_info')`.
- `alert_event` : `event_type IN ('opened','level_changed','recomputed','notified','vets_notified','escalated','reviewed','reopened','closed','cancelled')`.
- `disease_rule` : `cluster_window_days > 0` ; `cluster_min_reports >= 2` ; `cluster_min_ratio IS NULL OR (cluster_min_ratio > 0 AND cluster_min_ratio <= 1)` ; `escalation_hours > 0`.
- `movement` : `from_center_id <> to_center_id`.
- `habilitation` : `verified_by <> user_id` ; `valid_to >= valid_from`.
- `identity_support` : `support_type <> 'qr_label' OR label_id IS NOT NULL` ; UNIQUE partiel `(label_id) WHERE unbound_at IS NULL` ; UNIQUE partiel `(unit_id) WHERE support_type='qr_label' AND unbound_at IS NULL`.
- `label` : `short_code ~ '^[2-9A-HJ-NP-Z]{9}$'` (le 9e caractère est un caractère de contrôle calculé par l'application).
- `center_member` : UNIQUE partiel `(center_id) WHERE member_role='holder' AND ends_at IS NULL`.
- `movement_confirmation` : UNIQUE `(movement_id, side)`.
- `unit_open_movement` : clé primaire `unit_id`.
- `quarantine` : `center_id IS NOT NULL OR unit_id IS NOT NULL`.
- **Toute contrainte UNIQUE sur colonne nullable** : `NULLS NOT DISTINCT`.

## 8. Index à créer dès les migrations initiales
- `label(short_code)` unique (scan QR, requête la plus fréquente).
- `tracked_unit(current_center_id)` ; `identity_support(unit_id) WHERE unbound_at IS NULL`.
- Moteur d'exposition : `movement_item(unit_id, movement_id)` ; `movement(from_center_id, occurred_at)` ; `movement(to_center_id, occurred_at)` ; `movement(status)`.
- `alert(status, zone_id)` ; `alert(trigger_kind, status, zone_id)` (recherche d'une alerte de zone ouverte) ; `alert_review(alert_id)` ; `alert_exposure(alert_id, run_id)` ; `alert_exposure(center_id)` ; `zone_stat(zone_id, species_id)`.
- GIST : `zone(boundary)`, `center(location)`.
- `health_report(center_id, occurred_at DESC)` ; `health_report(status)`. Le comptage par zone (section 9.9) passe par `center.zone_id` (index créé automatiquement par Django sur la clé étrangère), puis `health_report(center_id, occurred_at DESC)` pour la fenêtre de dates, puis `health_report_subject` (clé `report_id, unit_id`) et `tracked_unit` pour l'espèce : **aucun index supplémentaire** tant qu'`EXPLAIN` ne montre pas de besoin.
- `sync_operation(device_id, server_seq)` ; `change_feed(center_id, seq)` ; `change_feed(zone_id, seq)`.
- `notification(user_id, status, created_at DESC)` ; `membership(user_id) WHERE ends_at IS NULL` ; `habilitation(user_id, status, valid_to)`.
- **Aucun autre index « au cas où »** : on l'ajoute quand une requête réelle le demande (`EXPLAIN`), puis on met ce fichier à jour.

## 9. Comportements métier à respecter (dans `services.py`)

### 9.1 Déclarer un mouvement (`traceability.services.declare_movement`)
Dans **une transaction** : (1) verrouiller les unités (`select_for_update`) ; (2) pour chaque unité, insérer dans `unit_open_movement` (échec = l'unité est déjà dans un mouvement : refuser) ; (3) vérifier que l'unité est bien dans le centre expéditeur (`tracked_unit.current_center_id`) ; (4) créer `movement` (statut `declared`), les `movement_item`, un `movement_status_event`, le code de confirmation ; (5) écrire `change_feed` et `audit_log`.

### 9.2 Double confirmation
Expéditeur puis destinataire confirment (`movement_confirmation`, une par côté). Quand les deux ont confirmé : statut `confirmed`, `movement.received_at` renseigné, `tracked_unit.current_center_id` mis à jour **par l'appel à `identity.services`**, `unit_open_movement` supprimé. Écart de quantité ou d'identité : `movement_discrepancy`, statut `partial` ou `disputed`. Délai dépassé sans confirmation : `expired`.

### 9.3 Fractionner un lot
Mouvement d'une partie d'un lot (ex. 10 poules sur 40) : à la confirmation, le service crée un **nouveau** `tracked_unit` (kind `lot`, `origin_unit_id` = lot d'origine) dans le centre destinataire, renseigne `movement_item.received_unit_id`, diminue `current_size` du lot d'origine et écrit un `status_event` `size_change`. Si tout le lot part : `received_unit_id` = la même unité.

### 9.4 Remplacer une étiquette
Dans une transaction : `identity_support.unbound_at` + `unbound_reason` sur l'ancien support, `label.status = 'deactivated'` ; nouveau support lié à la nouvelle étiquette. L'identifiant de l'unité ne change jamais. Un scan d'une étiquette désactivée affiche « étiquette remplacée » et renvoie vers l'unité.

### 9.5 Signalement et alerte
Une alerte a **deux déclencheurs** (`alert.trigger_kind`) :
- **`single_report`** (parcours d'origine) : `health_report` (cache `status`) -> évaluation par un vétérinaire (`health_report_review`, avec `habilitation_id` valide à cet instant, vérifié par le service) -> création/mise à jour d'`alert` (avec `focus_center_id`) -> calcul d'expositions.
- **`zone_cluster`** : plusieurs signalements similaires dans une même zone, pour une même espèce, sur une période -> le système repère un regroupement -> les vétérinaires de la zone confirment ou infirment (`alert_review`). Voir section 9.9.

Dans les deux cas : niveau 3 uniquement après validation par un vétérinaire habilité.

### 9.6 Calcul des expositions (`alerts.services.compute_exposures`)
1. Charger la règle (`alert.rule_id`) : fenêtres, profondeur, `include_unconfirmed`.
2. Partir de `alert.focus_center_id` ; pour une alerte de zone (`trigger_kind = 'zone_cluster'`), partir de **l'ensemble des centres ayant signalé** (`alert_report` -> `health_report.center_id`), chacun à la profondeur 0. Parcourir le graphe des mouvements : un centre est **exposé** s'il a reçu des unités d'un centre exposé (ou du foyer) dans la fenêtre `lookback_days`/`lookforward_days`, jusqu'à `max_depth` ; ne compter les mouvements `declared` que si `include_unconfirmed`. Suivre aussi la lignée des lots (`origin_unit_id`).
3. Utiliser une **CTE récursive** avec garde anti-boucle (tableau des centres déjà visités) et la borne de profondeur.
4. Écrire un nouveau `run_id` : une ligne `alert_exposure` par centre (ou unité) avec son statut, et une ligne `alert_exposure_step` par étape du chemin. **Écrire aussi les cas écartés** (`excluded_negative`) avec `explanation_code` (ex. `outside_window`).
5. Mettre à jour `alert.current_run_id` en dernier, dans la même transaction. Ne jamais supprimer les calculs précédents.
6. Notifier avec des messages **neutres** (`notification.message_code`), sans identité de l'élevage d'origine.

### 9.7 Synchronisation hors ligne
- L'appareil crée ses enregistrements avec leur UUID et envoie des opérations (`sync_operation.id` = UUID créé hors ligne).
- Le serveur applique `INSERT ... ON CONFLICT (id) DO NOTHING` : **rejouer une opération n'a aucun effet** (idempotence).
- `server_seq` donne l'ordre d'arrivée. Un conflit (ex. unité déjà déplacée) crée un `sync_conflict`, jamais un écrasement silencieux.
- Chaque écriture qui doit atteindre les autres appareils ajoute une ligne `change_feed` **dans la même transaction**, avec `center_id`/`zone_id` pour limiter ce que chaque appareil récupère.

### 9.8 Carte
`zone_stat` est recalculé par `geo.services`. Si l'effectif d'une zone est inférieur à `disease_rule.min_zone_effectif`, `is_masked = true` et aucune statistique fine n'est exposée. États : `normal`, `watch`, `exposure`, `alert`, `unknown`.

Correspondance avec les alertes (**proposition, à valider avec la charte**) :

| Situation | `zone_stat.state` |
|---|---|
| Alerte de zone en attente de confirmation par un vétérinaire | `watch` |
| Exposition potentielle (zone contenant des centres exposés) | `exposure` |
| Alerte validée (niveau 3) | `alert` |
| Zone masquée (effectif trop faible, `is_masked = true`) | `unknown` |

Quand plusieurs situations s'appliquent à une zone, l'état le plus grave l'emporte (`alert` > `exposure` > `watch` > `normal`) ; `unknown` (masquage) prime sur l'affichage pour respecter l'anonymat.

### 9.9 Regroupement de zone (`alerts.services.detect_zone_clusters`)

**Principes.** La détection est faite par **des règles explicables** lues dans `disease_rule`, jamais par une IA qui diagnostique. L'IA éventuelle reste secondaire et ne pose aucun diagnostic. Chaque alerte dit **pourquoi** elle existe (signalements comptés, période, effectif, seuil atteint). **Seul un vétérinaire habilité valide** (niveau 3). Un élevage **exposé n'est pas contaminé**.

**1. Détection.** Appelée après chaque signalement retenu comme compatible et périodiquement :
- compter, par couple (zone, espèce), les `health_report` compatibles dont `occurred_at` est dans les `cluster_window_days` derniers jours (zone = `center.zone_id` du centre signalant ; espèce = celle des unités de `health_report_subject` -> `tracked_unit.species_id`) ;
- rapporter le total d'animaux touchés (`affected_count`) à l'**effectif connu** des centres concernés pour cette espèce (unités actives : 1 par animal, `lot.current_size` par lot). 5 cas sur 10 animaux n'ont pas le même sens que 5 cas sur 1 000 ;
- seuil atteint si le nombre de signalements est `>= cluster_min_reports` **et**, quand `cluster_min_ratio` n'est pas NULL, le ratio est `>= cluster_min_ratio` ;
- **effectif inconnu** (aucune unité enregistrée de cette espèce dans un centre concerné) : le ratio n'est pas calculable pour ce centre ; on applique le seul seuil `cluster_min_reports` et l'alerte porte `confidence = 'reduced'`, affichée au vétérinaire.

**2. Création.** Si le seuil est atteint et qu'**aucune alerte de zone ouverte** n'existe pour (zone, espèce), dans une transaction : créer `alert` (`trigger_kind = 'zone_cluster'`, `level = 1`, `species_id`, `zone_id`, `focus_center_id` NULL, `confidence`), lier les signalements par `alert_report`, écrire `alert_event` `opened` (payload : nombre de signalements, ratio, seuils de la règle, version de la règle), fixer `escalation_due_at = opened_at + escalation_hours`. Si une alerte de zone est déjà ouverte : y ajouter les nouveaux signalements (`alert_report`).

**3. Notification des vétérinaires.** Destinataires : les utilisateurs ayant un `membership` actif de rôle `veterinarian` sur la zone **ou une de ses zones parentes**, **et** une `habilitation` valide (`status = 'verified'`, date du jour entre `valid_from` et `valid_to`). Message neutre (`notification.message_code`), type de notification dédié (ex. `kind = 'zone_cluster_review'`). Écrire `alert_event` `vets_notified`.

**4. Décision** (`alert_review`, avec `habilitation_id` valide vérifié par le service ; un vétérinaire sans habilitation valide est refusé) :
- `confirm` -> niveau 3 (`validated_by`, `validated_at`, `habilitation_id`), `alert_event` `reviewed` puis `level_changed` -> `compute_exposures` en partant des centres signalants (section 9.6) -> notifications neutres aux exposés -> recalcul de `zone_stat`. `escalation_due_at` passe à NULL.
- `dismiss` -> alerte fermée (`status = 'closed'`, `closed_at`) avec motif (`alert_review.note`), `alert_event` `reviewed` puis `closed` ; les signalements restent ré-évaluables.
- `need_info` -> l'alerte reste ouverte, `alert_event` `reviewed`.

**5. Relance.** Si aucune `alert_review` n'existe à `escalation_due_at` : `alert_event` `escalated` et nouvelle notification (autre vétérinaire habilité de la zone parente, ou autorité de la zone) ; `escalation_due_at` est reporté de `escalation_hours`.

**6. Réouverture** (proposition, à valider par le chef de projet). Après un `dismiss`, seuls les signalements **postérieurs à la décision** comptent pour ce couple (zone, espèce), sinon les mêmes signalements redéclencheraient aussitôt l'alerte. Si le seuil est de nouveau atteint dans la fenêtre, l'alerte infirmée est rouverte (`status = 'open'`, `alert_event` `reopened`, nouveaux signalements ajoutés par `alert_report`, nouvelle `escalation_due_at`) plutôt que dupliquée.

**Décision D11 à trancher par le chef de projet : désaccord entre vétérinaires.** Proposition par défaut : la **première décision** d'un vétérinaire habilité de la zone fait foi ; les décisions suivantes sont enregistrées (`alert_review`) sans changer l'état ; un désaccord (décisions différentes sur la même alerte) est signalé à l'autorité de la zone. Ne pas coder d'autre règle avant décision.

**Valeurs de démonstration** : `cluster_window_days`, `cluster_min_reports`, `cluster_min_ratio` et `escalation_hours` sont expérimentales et **à faire valider par un vétérinaire**.

## 10. Données de départ (`manage.py seed`, idempotent)
Chargées par migration de données ou commande, **jamais à la main** : `role` (breeder, field_agent, veterinarian, authority, trader), `species` (bovin, ovin, caprin, porcin, volaille avec `tracking_mode`), `symptom` et `disease` (liste courte, vocabulaire simple), `disease_rule` (version 1 par maladie ; valeurs **à faire valider par un vétérinaire**), au moins une `zone` de démonstration. Tout est marqué `is_simulated` quand c'est de la donnée de démonstration.

## 11. Évolution du schéma
- Ajouter une colonne NULL ou avec défaut, une table, un index : normal.
- Renommer ou supprimer : en trois temps (ajouter, migrer code et données, supprimer plus tard).
- Changer un type ou resserrer une contrainte : migration dédiée relue par le chef de projet.
- Règle sanitaire : nouvelle version de `disease_rule`, jamais de modification.
- Tout changement du schéma : demande de fusion dont le titre commence par `schema:`, qui **modifie aussi ce fichier**.

## 12. Tests obligatoires par application
Chaque application livre au minimum des tests qui prouvent :
- création d'un enregistrement valide ; refus d'un enregistrement qui viole chaque `CHECK` et chaque `UNIQUE` de ses tables (y compris les cas avec NULL) ;
- pour les événements : tentative de `UPDATE` et de `DELETE` (ORM **et** SQL brut) = erreur ;
- `identity` : une étiquette active ne peut être liée à deux unités ; remplacer une étiquette conserve l'historique ;
- `traceability` : une unité ne peut pas être dans deux mouvements ouverts ; la double confirmation met à jour le centre courant ; le fractionnement d'un lot crée la bonne lignée ;
- `alerts` : alerte niveau 3 refusée sans habilitation valide ; le calcul est rejouable (nouveau `run_id`) ; le cas négatif est enregistré ; la profondeur est respectée ;
- `alerts`, regroupement de zone : un regroupement qui atteint le seuil déclenche une alerte `zone_cluster` ; un cas isolé ne déclenche aucune alerte ; des signalements d'espèces différentes ne forment pas de regroupement ; le ratio est rapporté à l'effectif connu (même nombre de cas : seuil atteint sur un petit effectif, pas sur un grand) ; effectif inconnu = `confidence = 'reduced'` ; seuls les vétérinaires habilités de la zone (zones parentes incluses) sont notifiés ; relance (`escalated`) à `escalation_due_at` sans réponse ; confirmation par un vétérinaire sans habilitation valide refusée ; alerte de zone sans `species_id` refusée par la base ; `alert_review` en ajout seul (UPDATE/DELETE refusés) ;
- `sync` : rejouer deux fois la même opération = un seul effet ;
- API : un éleveur exposé ne voit jamais l'identité de l'élevage d'origine.

## 13. Définition de « terminé » pour un modèle
- [ ] Classe et `db_table` conformes à la section 6, bonne base héritée.
- [ ] Tous les `CHECK`, `UNIQUE`, `NULLS NOT DISTINCT` et index de la table présents dans la migration.
- [ ] Triggers de la section 7 appliqués si la table est concernée.
- [ ] Colonnes CALCULÉ en `editable=False`, écrites seulement dans `services.py`.
- [ ] Tests de la section 12 écrits et verts.
- [ ] `python manage.py makemigrations --check` ne détecte aucun écart.
- [ ] Aucune règle sanitaire en dur, aucun secret, aucune donnée réelle.
