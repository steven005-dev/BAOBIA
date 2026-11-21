"""Fiches maladie : ce qui relie un signalement à une maladie (aide au vétérinaire).

À VALIDER PAR UN VÉTÉRINAIRE. Rédigées à partir des fiches techniques de l'Organisation
mondiale de la santé animale (OMSA / WOAH) pour le prototype ; elles ne posent AUCUN
diagnostic : elles donnent des PISTES que le vétérinaire vérifie sur place.

Pour chaque maladie (code du catalogue, apps/health/catalog.py) :
- species : espèces sensibles ;
- major / suggestive : codes des symptômes de l'éleveur (catalog.SYMPTOMS) qui sont des
  signes majeurs ou seulement évocateurs ;
- missing_sign : signe clé que l'éleveur ne peut pas cocher (absent de la liste simple) ;
- mortality : part de morts habituelle chez les animaux touchés (low < 10 %, variable,
  high >= 30 %) ;
- spread : contagion rapide ou lente ;
- incubation_days : (min, max) ;
- zoonosis : transmissible à l'humain (précautions pour la personne qui prélève) ;
- samples : prélèvements conseillés (nature, conditionnement) ;
- caution : consigne de prudence propre à la maladie (facultatif).
Le laboratoire de référence est à confirmer par l'autorité vétérinaire (LAB_NOTE).

Source de la version 2 (21/11) : docs/fiches_maladies_animales_CI.txt (12 fiches, d'après
l'OMSA ; les fiches marquées [*] sont à faire confirmer par un vétérinaire). Les signes de
ce fichier sans case pour l'éleveur (torticolis, avortements, changement de comportement...)
sont dans missing_sign : le vétérinaire les vérifie sur place.
"""

VERSION = 2
VALIDATED = False  # passe à True quand un vétérinaire a relu et signé les fiches
# Signe d'alerte général (fichier des fiches) : rappelé au vétérinaire sur chaque signalement.
GENERAL_ALERT = ("Plusieurs bêtes malades ou mortes en peu de temps : isoler les animaux, ne rien "
                 "déplacer, prévenir les services vétérinaires de la zone.")

LAB_NOTE = ("Laboratoire de référence à confirmer par l'autorité vétérinaire "
            "(en Côte d'Ivoire, le LANADA). Échantillons au froid (+4 °C), jamais congelés "
            "sauf indication du laboratoire.")

PROFILES = {
    "fmd": {
        "species": ("cattle", "sheep", "goat", "pig"),
        "major": ("mouth_drool", "lameness", "fever"),
        "suggestive": ("not_eating",),
        "missing_sign": "Aphtes (vésicules) sur la langue, les gencives, entre les onglons",
        "mortality": "low",
        "spread": "rapid",
        "incubation_days": (2, 14),
        "zoonosis": False,
        "samples": (
            ("Épithélium ou liquide d'aphtes", "Milieu de transport, au froid"),
            ("Sang sur tube sec (sérum)", "Au froid"),
        ),
    },
    "lsd": {
        "species": ("cattle",),
        "major": ("skin_lesions", "fever"),
        "suggestive": ("not_eating", "mouth_drool", "lameness"),
        "missing_sign": "Nodules fermes sur la peau, ganglions gonflés",
        "mortality": "low",
        "spread": "slow",
        "incubation_days": (4, 28),
        "zoonosis": False,
        "samples": (
            ("Biopsie ou croûte de nodule cutané", "Tube sec, au froid"),
            ("Sang sur tube EDTA", "Au froid"),
        ),
    },
    "cbpp": {
        "species": ("cattle",),
        "major": ("breathing", "fever"),
        "suggestive": ("not_eating", "sudden_death"),
        "missing_sign": "Douleur thoracique, animal tête tendue, toux sèche",
        "mortality": "variable",
        "spread": "slow",
        "incubation_days": (21, 180),
        "zoonosis": False,
        "samples": (
            ("Sang sur tube sec (sérologie)", "Au froid"),
            ("Liquide pleural ou poumon (animal mort)", "Au froid"),
        ),
    },
    "ppr": {
        "species": ("sheep", "goat"),
        "major": ("fever", "diarrhea", "mouth_drool", "breathing"),
        "suggestive": ("not_eating", "sudden_death"),
        "missing_sign": "Écoulements des yeux et du nez",
        "mortality": "high",
        "spread": "rapid",
        "incubation_days": (3, 10),
        "zoonosis": False,
        "samples": (
            ("Écouvillons des yeux, du nez et de la bouche", "Milieu de transport, au froid"),
            ("Sang sur tube EDTA", "Au froid"),
        ),
    },
    "trypanosomosis": {
        "species": ("cattle", "sheep", "goat"),
        "major": ("fever", "not_eating"),
        "suggestive": ("diarrhea",),
        "missing_sign": "Amaigrissement progressif, muqueuses pâles (anémie)",
        "mortality": "variable",
        "spread": "slow",
        "incubation_days": (7, 28),
        "zoonosis": False,
        "samples": (
            ("Sang sur tube EDTA (frottis, recherche du parasite)", "Au froid, analyse rapide"),
        ),
    },
    "brucellosis": {
        "species": ("cattle", "sheep", "goat"),
        "major": (),
        "suggestive": ("lameness", "fever"),
        "missing_sign": "Avortements en fin de gestation (signe principal)",
        "mortality": "low",
        "spread": "slow",
        "incubation_days": (14, 180),
        "zoonosis": True,
        "caution": "Transmissible à l'homme (lait cru, produits d'avortement) : manipuler avec gants.",
        "samples": (
            ("Sang sur tube sec (sérologie)", "Au froid"),
            ("Avorton ou placenta", "Sac étanche, au froid ; gants et masque"),
        ),
    },
    "asf": {
        "species": ("pig",),
        "major": ("fever", "sudden_death", "skin_lesions", "not_eating"),
        "suggestive": ("diarrhea", "breathing"),
        "missing_sign": "Rougeurs ou taches violettes sur les oreilles et le ventre",
        "mortality": "high",
        "spread": "rapid",
        "incubation_days": (4, 19),
        "zoonosis": False,
        "samples": (
            ("Sang sur tube EDTA", "Au froid"),
            ("Rate, ganglions (animal mort)", "Au froid"),
        ),
    },
    "avian_influenza": {
        "species": ("poultry",),
        "major": ("sudden_death", "breathing"),
        "suggestive": ("not_eating", "diarrhea", "skin_lesions"),
        "missing_sign": "Crête violacée, gonflement de la tête, baisse brutale de la ponte",
        "mortality": "high",
        "spread": "rapid",
        "incubation_days": (3, 14),
        "zoonosis": True,
        "caution": "Peut toucher l'homme : ne pas manipuler les oiseaux morts à mains nues.",
        "samples": (
            ("Écouvillons de la trachée et du cloaque", "Milieu de transport, au froid"),
            ("Cadavres entiers", "Sac étanche, au froid ; gants, masque, lunettes"),
        ),
    },
    # --- Ajoutées le 21/11 (fiches 9 à 12 du fichier, marquées [*] : à confirmer) ---
    "newcastle": {
        "species": ("poultry",),
        "major": ("sudden_death", "breathing"),
        "suggestive": ("not_eating", "diarrhea"),
        "missing_sign": "Torticolis, paralysie, chute de ponte, diarrhée verdâtre",
        "mortality": "high",
        "spread": "rapid",
        "incubation_days": (2, 15),
        "zoonosis": False,
        "caution": "Proche de la grippe aviaire : à distinguer au laboratoire. Se prévient par la vaccination.",
        "samples": (
            ("Écouvillons de la trachée et du cloaque", "Milieu de transport, au froid"),
            ("Cadavres entiers", "Sac étanche, au froid"),
        ),
    },
    "anthrax": {
        "species": ("cattle", "sheep", "goat"),
        "major": ("sudden_death", "fever"),
        "suggestive": ("not_eating",),
        "missing_sign": "Sang noir qui sort par les orifices, cadavre qui gonfle vite, gonflements",
        "mortality": "high",
        "spread": "soil",
        "incubation_days": (1, 14),
        "zoonosis": True,
        "caution": "NE PAS OUVRIR LA CARCASSE. Dangereux pour l'homme : seul le vétérinaire intervient.",
        "samples": (
            ("Sang prélevé à l'oreille ou à la queue, sans ouvrir le cadavre", "Tube étanche, au froid ; gants"),
        ),
    },
    "rift_valley_fever": {
        "species": ("cattle", "sheep", "goat"),
        "major": ("fever", "sudden_death"),
        "suggestive": ("not_eating",),
        "missing_sign": "Avortements en nombre, jeunes qui meurent vite, grande faiblesse",
        "mortality": "high",
        "spread": "vector",
        "incubation_days": (1, 6),
        "zoonosis": True,
        "caution": "Transmissible à l'homme (sang, avortons) : gants, masque, lunettes.",
        "samples": (
            ("Sang sur tube EDTA et sur tube sec", "Au froid ; gants"),
            ("Avorton (foie)", "Sac étanche, au froid ; gants et masque"),
        ),
    },
    "rabies": {
        "species": ("cattle", "sheep", "goat", "pig"),
        "major": ("mouth_drool",),
        "suggestive": ("lameness",),
        "missing_sign": "Changement de comportement (agressivité ou grande tristesse), paralysie, "
                        "morsure par un animal inconnu",
        "mortality": "high",
        "spread": "bite",
        "incubation_days": (14, 180),
        "zoonosis": True,
        "caution": "Mortelle pour l'homme. Après une morsure : laver à l'eau et au savon, aller à "
                   "l'hôpital. Ne pas toucher la bave.",
        "samples": (
            ("Tête de l'animal mort, entière", "Par le vétérinaire seulement ; sac étanche, au froid"),
        ),
    },
}

MORTALITY_LABELS = {"low": "faible", "variable": "variable", "high": "forte"}
SPREAD_LABELS = {
    "rapid": "rapide",
    "slow": "lente",
    "soil": "par les spores du sol (pas de bête à bête)",
    "vector": "par les moustiques et le sang",
    "bite": "par morsure",
}
