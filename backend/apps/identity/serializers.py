"""Formes des données des routes identity (entrées et réponses, pour le schéma API).

Aucune règle métier ici : les sérialiseurs d'entrée valident la forme, les services
font le travail. Les champs CALCULÉ (current_center, life_status, current_size)
ne sont jamais acceptés en entrée.
"""

from rest_framework import serializers

CENTER_TYPES = ("farm", "market", "slaughterhouse", "checkpoint", "other")
SEXES = ("male", "female", "unknown")
BIRTH_PRECISIONS = ("day", "month", "year", "estimated")


class NamedRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class SpeciesRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    label_fr = serializers.CharField()
    tracking_mode = serializers.CharField()


# --------------------------------------------------------------------------- Centres

class CenterListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    center_type = serializers.CharField()
    zone_id = serializers.UUIDField()
    access = serializers.ChoiceField(
        choices=("holder", "co_holder", "worker", "mandate"),
        help_text="Pourquoi l'utilisateur a accès : membre du centre ou mandat.",
    )


class CenterCreateSerializer(serializers.Serializer):
    id = serializers.UUIDField(
        required=False,
        help_text="UUID créé sur l'appareil (hors ligne). Renvoyer le même id = sans effet.",
    )
    name = serializers.CharField(max_length=160)
    zone_id = serializers.UUIDField()
    center_type = serializers.ChoiceField(choices=CENTER_TYPES, default="farm")
    species_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)


class CenterDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    center_type = serializers.CharField()
    status = serializers.CharField()
    zone = NamedRefSerializer()
    species = SpeciesRefSerializer(many=True)
    animals_count = serializers.IntegerField(help_text="Animaux actifs présents.")
    lots_count = serializers.IntegerField(help_text="Lots actifs présents.")
    heads_count = serializers.IntegerField(help_text="Têtes connues : animaux + effectif des lots.")
    is_simulated = serializers.BooleanField()


# --------------------------------------------------------------------------- Unités

class UnitCreateSerializer(serializers.Serializer):
    id = serializers.UUIDField(
        required=False,
        help_text="UUID créé sur l'appareil (hors ligne). Renvoyer le même id = sans effet.",
    )
    kind = serializers.ChoiceField(choices=("animal", "lot"))
    center_id = serializers.UUIDField()
    species_id = serializers.UUIDField()
    local_name = serializers.CharField(max_length=60, required=False, allow_blank=True)
    label_code = serializers.CharField(
        max_length=20, required=False, allow_blank=True,
        help_text="Code de l'étiquette, créé par le téléphone (8 caractères + 1 de contrôle) ; "
                  "l'étiquette est créée si le code est nouveau.",
    )
    # Animal
    sex = serializers.ChoiceField(choices=SEXES, default="unknown")
    birth_date = serializers.DateField(required=False, allow_null=True)
    birth_date_precision = serializers.ChoiceField(
        choices=BIRTH_PRECISIONS, required=False, allow_null=True
    )
    breed = serializers.CharField(max_length=60, required=False, allow_blank=True)
    marks = serializers.CharField(required=False, allow_blank=True)
    # Lot
    size = serializers.IntegerField(required=False, min_value=1, help_text="Effectif d'un lot.")
    description = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["kind"] == "lot" and not attrs.get("size"):
            raise serializers.ValidationError({"size": "Indiquez le nombre d'animaux du lot."})
        return attrs


class AnimalDetailSerializer(serializers.Serializer):
    sex = serializers.CharField()
    birth_date = serializers.DateField(allow_null=True)
    birth_date_precision = serializers.CharField(allow_null=True)
    breed = serializers.CharField(allow_null=True)
    marks = serializers.CharField(allow_null=True)


class LotDetailSerializer(serializers.Serializer):
    current_size = serializers.IntegerField()
    description = serializers.CharField(allow_null=True)


class UnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    species = SpeciesRefSerializer()
    local_name = serializers.CharField(allow_null=True)
    life_status = serializers.CharField()
    current_center = NamedRefSerializer(allow_null=True)
    label_code = serializers.CharField(allow_null=True, help_text="Étiquette QR active.")
    animal = AnimalDetailSerializer(allow_null=True)
    lot = LotDetailSerializer(allow_null=True)
    created_at = serializers.DateTimeField()
    is_simulated = serializers.BooleanField()


class UnitListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    species = SpeciesRefSerializer()
    local_name = serializers.CharField(allow_null=True)
    life_status = serializers.CharField()
    label_code = serializers.CharField(allow_null=True)
    size = serializers.IntegerField(help_text="1 pour un animal, effectif pour un lot.")


# --------------------------------------------------------------------------- Scan

class ScanResultSerializer(serializers.Serializer):
    result = serializers.ChoiceField(
        choices=("found", "replaced", "lost"),
        help_text="found = étiquette posée ; replaced = étiquette remplacée (fiche de l'animal "
                  "qui la portait) ; lost = étiquette déclarée perdue.",
    )
    message = serializers.CharField(help_text="Message court du vocabulaire officiel.")
    label_code = serializers.CharField()
    full_access = serializers.BooleanField(
        help_text="false = vue réduite (espèce seulement), sans élevage ni détail."
    )
    unit = UnitSerializer(allow_null=True)
    species = SpeciesRefSerializer()


class LabelReplaceSerializer(serializers.Serializer):
    label_code = serializers.CharField(
        max_length=20, help_text="Code de la nouvelle étiquette, créé par le téléphone ; créée si nouvelle."
    )
    reason = serializers.ChoiceField(
        choices=("lost", "damaged", "error"),
        help_text="lost = perdue ; damaged = abîmée ; error = mauvaise étiquette posée.",
    )


class VerificationCreateSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, help_text="UUID créé sur le téléphone : rejouer = sans effet.")
    label_code = serializers.CharField(max_length=20, help_text="Code lu ou saisi.")
    method = serializers.ChoiceField(choices=("scan", "manual_code"), default="scan")
    occurred_at = serializers.DateTimeField(help_text="Heure du scan sur le téléphone.")
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True,
                                        min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True,
                                         min_value=-180, max_value=180)
    accuracy_m = serializers.DecimalField(max_digits=7, decimal_places=1, required=False, allow_null=True,
                                          min_value=0)


class VerificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    result = serializers.ChoiceField(choices=("confirmed", "mismatch", "unreadable"))
    occurred_at = serializers.DateTimeField()


class ZoneItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    level = serializers.IntegerField(help_text="0 = pays, 1 = région, 2 = département...")
    parent_id = serializers.UUIDField(allow_null=True)


class LabelIssueSerializer(serializers.Serializer):
    codes = serializers.ListField(
        child=serializers.CharField(max_length=20), min_length=1, max_length=200,
        help_text="Codes des étiquettes vierges remises à l'élevage (scannés ou saisis).",
    )


class LabelIssuedSerializer(serializers.Serializer):
    issued = serializers.IntegerField()
    codes = serializers.ListField(child=serializers.CharField())


class LabelBatchCreateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=500)
    note = serializers.CharField(max_length=160, required=False, allow_blank=True)


class LabelBatchSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    quantity = serializers.IntegerField()
    codes = serializers.ListField(child=serializers.CharField(), help_text="Codes à imprimer.")
