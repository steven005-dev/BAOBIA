"""Numéros officiels (boucles Vet'Tronic, 15 chiffres) pour les animaux SIMULÉS (21/11).

Décision du chef de projet : l'identifiant des animaux est le numéro officiel de la boucle
(384 = Côte d'Ivoire, norme ISO 11784) ; le code QR BAOBIA reste sur l'étiquette, en plus.
Bovins, moutons et chèvres seulement (espèces du pilote d'identification) : porcs et
volailles gardent le code BAOBIA.

Le numéro d'un animal est toujours le même (tiré de son identifiant) : « 3841 » + 11 chiffres,
hors de la plage des boucles de démonstration de Romuald (3840000000…). Idempotent : un
animal qui a déjà une boucle active est laissé tel quel. Écrit par traceability.bind_rfid_tag.
"""

from django.contrib.auth import get_user_model

OFFICIAL_SPECIES = ("cattle", "sheep", "goat")
DEMO_AGENT_PHONE = "+2250000000005"


def demo_number(unit_id, attempt=0):
    return "3841" + str((int(unit_id.hex, 16) + attempt) % 10 ** 11).zfill(11)


def assign_official_tags():
    """Pose un numéro officiel sur chaque animal simulé qui n'en a pas. Retourne le nombre."""
    from apps.identity.models import TrackedUnit
    from apps.traceability.models import RfidTag
    from apps.traceability.services import bind_rfid_tag

    agent = get_user_model().objects.filter(phone=DEMO_AGENT_PHONE).first()
    if agent is None:
        return 0
    tagged = RfidTag.objects.filter(status="active").values_list("unit_id", flat=True)
    units = (TrackedUnit.objects.filter(is_simulated=True, kind="animal",
                                        species__code__in=OFFICIAL_SPECIES)
             .exclude(life_status__in=("dead", "slaughtered", "closed"))
             .exclude(id__in=tagged).order_by("created_at"))
    count = 0
    for unit in units:
        attempt = 0
        while RfidTag.objects.filter(number=demo_number(unit.pk, attempt), status="active").exists():
            attempt += 1
        bind_rfid_tag(unit_id=unit.pk, number=demo_number(unit.pk, attempt),
                      read_mode="manual_entry", created_by=agent)
        count += 1
    return count
