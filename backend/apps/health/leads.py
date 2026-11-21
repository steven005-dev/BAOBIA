"""Pistes de maladie pour un signalement (aide au vétérinaire, AUCUN diagnostic).

Règles, dans cet ordre (toutes explicables, écrites dans la réponse) :
1. Espèce : une maladie n'est proposée que si l'espèce du signalement y est sensible
   (si le signalement ne cite aucun animal, l'espèce n'est pas filtrée et c'est dit).
2. Signes : on compte les signes MAJEURS et ÉVOCATEURS de la fiche que l'éleveur a cochés.
   - piste forte : au moins 2 signes majeurs, et au moins la moitié des signes majeurs ;
   - piste moyenne : au moins 1 signe majeur ;
   - piste faible : seulement des signes évocateurs ;
   - aucun signe de la fiche : la maladie n'est pas proposée.
3. Part de morts (morts / animaux touchés) comparée à la fiche : si elle ne correspond pas
   (ex. beaucoup de morts pour une maladie qui tue peu), la piste baisse d'un cran.
Le vétérinaire examine et décide ; les fiches sont à valider (disease_profiles.VALIDATED).
"""

from .disease_profiles import (GENERAL_ALERT, LAB_NOTE, MORTALITY_LABELS, PROFILES, SPREAD_LABELS,
                               VALIDATED, VERSION)

STRENGTHS = ("strong", "medium", "weak")
STRENGTH_LABELS = {"strong": "piste forte", "medium": "piste moyenne", "weak": "piste faible"}


def _mortality_class(dead, affected):
    if not affected:
        return None
    ratio = dead / affected
    if ratio >= 0.3:
        return "high"
    if ratio < 0.1:
        return "low"
    return "variable"


def disease_leads(report):
    """Liste des pistes, de la plus forte à la plus faible, avec leurs explications."""
    from .models import Disease, Symptom

    symptom_codes = set(report.symptoms.values_list("code", flat=True))
    symptom_labels = dict(report.symptoms.values_list("code", "label_fr"))
    species_codes = set(report.subjects.values_list("unit__species__code", flat=True))
    observed = _mortality_class(report.dead_count, report.affected_count)
    all_labels = dict(Symptom.objects.values_list("code", "label_fr"))

    def label(code):
        return symptom_labels.get(code) or all_labels.get(code, code)

    leads = []
    for disease in Disease.objects.filter(is_active=True, code__in=list(PROFILES)):
        profile = PROFILES[disease.code]
        sensitive = species_codes & set(profile["species"])
        if species_codes and not sensitive:
            continue  # espèce non sensible : pas de piste
        majors = [c for c in profile["major"] if c in symptom_codes]
        suggestive = [c for c in profile["suggestive"] if c in symptom_codes]
        total = len(profile["major"])
        if majors and len(majors) >= 2 and len(majors) * 2 >= total:
            strength = "strong"
        elif majors:
            strength = "medium"
        elif suggestive:
            strength = "weak"
        else:
            continue

        lines = []
        if sensitive:
            lines.append("Espèce sensible.")
        else:
            lines.append("Espèce non précisée dans le signalement.")
        if total:
            lines.append(f"{len(majors)} signe(s) majeur(s) sur {total}"
                         + (f" : {', '.join(label(c) for c in majors)}." if majors else "."))
        missing = [c for c in profile["major"] if c not in symptom_codes]
        if missing:
            lines.append(f"Signes majeurs absents : {', '.join(label(c) for c in missing)}.")
        if suggestive:
            lines.append(f"Signes évocateurs : {', '.join(label(c) for c in suggestive)}.")

        expected = profile["mortality"]
        coherent = None
        if observed and expected != "variable" and observed != "variable":
            coherent = observed == expected
        if observed:
            lines.append(
                f"{report.dead_count} mort(s) sur {report.affected_count} animal(aux) touché(s) ; "
                f"part de morts habituelle : {MORTALITY_LABELS[expected]}"
                + (" (cohérent)." if coherent else " (inhabituel)." if coherent is False else ".")
            )
        if coherent is False:
            strength = STRENGTHS[min(STRENGTHS.index(strength) + 1, len(STRENGTHS) - 1)]
        lines.append(f"À vérifier sur place : {profile['missing_sign']}.")

        leads.append({
            "disease": {"code": disease.code, "label_fr": disease.label_fr,
                        "is_notifiable": disease.is_notifiable},
            "strength": strength,
            "strength_label": STRENGTH_LABELS[strength],
            "major_found": len(majors),
            "major_total": total,
            "explanation": lines,
            "spread": SPREAD_LABELS[profile["spread"]],
            "incubation_days": list(profile["incubation_days"]),
            "zoonosis": profile["zoonosis"],
            "caution": profile.get("caution"),
            "samples": [{"nature": n, "conditioning": c} for n, c in profile["samples"]],
        })
    leads.sort(key=lambda lead: (STRENGTHS.index(lead["strength"]), -lead["major_found"],
                                 lead["disease"]["label_fr"]))
    return leads


def leads_payload(report):
    return {
        "items": disease_leads(report),
        "profiles_version": VERSION,
        "validated": VALIDATED,
        "lab_note": LAB_NOTE,
        "general_alert": GENERAL_ALERT,
        "diseases_count": len(PROFILES),
        "warning": "Pistes calculées à partir des signes cochés par l'éleveur : ce n'est pas un "
                   "diagnostic. Le vétérinaire examine les animaux et décide.",
    }
