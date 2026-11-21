"""Catalogue de départ du module health : maladies et symptômes.

PROVISOIRE : liste courte pour le prototype, À FAIRE VALIDER PAR UN VÉTÉRINAIRE
(cahier des charges, section 12 ; charte, section 15 : 6 à 8 symptômes au plus).
- Maladies : priorités citées dans l'état des lieux de l'élevage en Côte d'Ivoire.
  `is_notifiable` reste à False tant que la liste officielle ivoirienne des
  maladies à déclaration obligatoire n'est pas obtenue.
- Symptômes : formulés pour un éleveur qui n'a pas à connaître le nom de la maladie.
  `icon` = nom provisoire de pictogramme (les pictogrammes de symptômes restent
  à dessiner, voir la charte).

Les codes d'espèces sont ceux du seed de core : cattle, sheep, goat, pig, poultry.
"""

RUMINANTS = ("cattle", "sheep", "goat")
ALL_SPECIES = ("cattle", "sheep", "goat", "pig", "poultry")

# code, libellé, espèces
DISEASES = (
    ("fmd", "Fièvre aphteuse", ("cattle", "sheep", "goat", "pig")),
    ("lsd", "Dermatose nodulaire contagieuse", ("cattle",)),
    ("cbpp", "Péripneumonie contagieuse bovine", ("cattle",)),
    ("ppr", "Peste des petits ruminants", ("sheep", "goat")),
    ("trypanosomosis", "Trypanosomose", RUMINANTS),
    ("brucellosis", "Brucellose", RUMINANTS),
    ("asf", "Peste porcine africaine", ("pig",)),
    ("avian_influenza", "Grippe aviaire", ("poultry",)),
    # Ajoutées le 21/11 (docs/fiches_maladies_animales_CI.txt, à confirmer par un vétérinaire).
    ("newcastle", "Maladie de Newcastle", ("poultry",)),
    ("anthrax", "Charbon bactéridien", RUMINANTS),
    ("rift_valley_fever", "Fièvre de la Vallée du Rift", RUMINANTS),
    ("rabies", "Rage", ("cattle", "sheep", "goat", "pig")),
)

# code, libellé simple, icône provisoire, espèces
SYMPTOMS = (
    ("not_eating", "Ne mange plus", "utensils-crossed", ALL_SPECIES),
    ("fever", "Corps chaud, fièvre", "thermometer", ALL_SPECIES),
    ("diarrhea", "Diarrhée", "droplets", ALL_SPECIES),
    ("breathing", "Tousse, respire mal", "wind", ALL_SPECIES),
    ("lameness", "Boite, marche mal", "footprints", ("cattle", "sheep", "goat", "pig")),
    ("skin_lesions", "Boutons ou plaies sur la peau", "scan-face", ALL_SPECIES),
    ("mouth_drool", "Bave, plaies dans la bouche", "droplet", ("cattle", "sheep", "goat", "pig")),
    ("sudden_death", "Mort soudaine", "skull", ALL_SPECIES),
)
