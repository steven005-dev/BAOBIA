"""Fonctions publiques du module health (responsable : Yéo).

Les autres modules n'écrivent JAMAIS dans les tables de health : ils appellent
ces fonctions. La colonne CALCULÉ health_report.status n'est écrite qu'ici.

Catalogue :
- load_catalog() : maladies et symptômes de départ (idempotent)
"""

from django.db import transaction

from apps.core.models import Species

from . import catalog
from .models import Disease, DiseaseSpecies, Symptom, SymptomSpecies


class HealthError(Exception):
    """Erreur métier du module health ; le message est lisible par l'utilisateur."""


@transaction.atomic
def load_catalog():
    """Crée les maladies et symptômes du catalogue de départ, et leurs espèces.

    Idempotent : ne crée que ce qui manque, ne modifie jamais une ligne existante.
    Exige les espèces du seed de core. Retourne la liste des éléments créés.
    """
    codes = {code for *_, species in (*catalog.DISEASES, *catalog.SYMPTOMS) for code in species}
    species = {s.code: s for s in Species.objects.filter(code__in=codes)}
    missing = sorted(codes - species.keys())
    if missing:
        raise HealthError(
            "Espèces absentes : " + ", ".join(missing) + ". Lancez d'abord manage.py seed."
        )

    created = []
    for code, label, species_codes in catalog.DISEASES:
        disease, is_new = Disease.objects.get_or_create(code=code, defaults={"label_fr": label})
        if is_new:
            created.append(f"maladie {code}")
        for species_code in species_codes:
            DiseaseSpecies.objects.get_or_create(disease=disease, species=species[species_code])

    for code, label, icon, species_codes in catalog.SYMPTOMS:
        symptom, is_new = Symptom.objects.get_or_create(
            code=code, defaults={"label_fr": label, "icon": icon}
        )
        if is_new:
            created.append(f"symptôme {code}")
        for species_code in species_codes:
            SymptomSpecies.objects.get_or_create(symptom=symptom, species=species[species_code])
    return created
