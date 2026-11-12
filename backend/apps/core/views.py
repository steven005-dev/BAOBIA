"""Catalogue partagé : espèces (lecture seule)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Species


class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = ("id", "code", "label_fr", "tracking_mode")


class SpeciesListView(APIView):
    @extend_schema(
        tags=["Catalogue"],
        summary="Espèces",
        description="Espèces actives. tracking_mode : animal (suivi individuel), lot, ou both.",
        responses={200: SpeciesSerializer(many=True)},
    )
    def get(self, request):
        species = Species.objects.filter(is_active=True).order_by("label_fr")
        return Response(SpeciesSerializer(species, many=True).data)
