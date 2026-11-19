"""Sérialiseurs de l'API health. Les champs suivent docs/CONTRAT_SANTE_MOUVEMENTS.md."""

from rest_framework import serializers

from .models import HealthReport, HealthReportReview, HealthReportSubject


class CatalogItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    label_fr = serializers.CharField()
    icon = serializers.CharField(allow_null=True, required=False)


class SubjectInSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField()
    condition = serializers.ChoiceField(choices=HealthReportSubject.Condition.choices)
    notes = serializers.CharField(max_length=200, required=False, allow_blank=True)


class ReportCreateSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="UUID de l'opération créé sur le téléphone.")
    center_id = serializers.UUIDField()
    report_kind = serializers.ChoiceField(choices=HealthReport.Kind.choices)
    affected_count = serializers.IntegerField(min_value=1)
    self_severity = serializers.ChoiceField(choices=HealthReport.Severity.choices)
    occurred_at = serializers.DateTimeField(help_text="Date d'observation (téléphone).")
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False,
                                        allow_null=True, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False,
                                         allow_null=True, min_value=-180, max_value=180)
    position_accuracy_m = serializers.DecimalField(max_digits=7, decimal_places=1,
                                                   required=False, allow_null=True, min_value=0)
    position_source = serializers.ChoiceField(
        choices=("gps", "network", "manual", "none"), default="none"
    )
    symptom_codes = serializers.ListField(
        child=serializers.CharField(max_length=30), required=False, default=list, max_length=20
    )
    subjects = SubjectInSerializer(many=True, required=False, default=list, max_length=200)

    def validate(self, data):
        has_position = data.get("latitude") is not None and data.get("longitude") is not None
        if (data.get("latitude") is None) != (data.get("longitude") is None):
            raise serializers.ValidationError("Position incomplète.")
        if not has_position:
            data["position_source"] = "none"
        return data


class ReviewCreateSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    decision = serializers.ChoiceField(choices=HealthReportReview.Decision.choices)
    disease_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ReviewOutSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    decision = serializers.CharField()
    disease = CatalogItemSerializer(allow_null=True)
    note = serializers.CharField(allow_null=True)
    vet_name = serializers.CharField()
    occurred_at = serializers.DateTimeField()


class SubjectOutSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField()
    condition = serializers.CharField()
    species_code = serializers.CharField()
    local_name = serializers.CharField(allow_null=True)


class CenterRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    zone_id = serializers.UUIDField()


class ReportOutSerializer(serializers.Serializer):
    """Vu par le déclarant ou l'élevage : son signalement et son état (SA-04).
    Les professionnels reçoivent en plus `reviews` et `position`."""

    id = serializers.UUIDField()
    center = CenterRefSerializer()
    report_kind = serializers.CharField()
    affected_count = serializers.IntegerField()
    self_severity = serializers.CharField()
    note = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    occurred_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    is_simulated = serializers.BooleanField()
    symptoms = CatalogItemSerializer(many=True)
    subjects = SubjectOutSerializer(many=True)
    reviews = ReviewOutSerializer(many=True, required=False)
    position = serializers.DictField(required=False, allow_null=True)
