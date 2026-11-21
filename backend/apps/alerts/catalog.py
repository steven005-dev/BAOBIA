"""Règles sanitaires de DÉMONSTRATION (version 1), chargées par manage.py seed_alerts.

EXPÉRIMENTAL : ces valeurs ne viennent pas d'un vétérinaire. Elles servent à montrer
le fonctionnement du prototype et doivent être remplacées par des valeurs validées
par l'autorité vétérinaire (RG-10, spec 9.9). Le moteur ne contient aucune de ces
valeurs : il lit toujours la table disease_rule.

min_zone_effectif = 2 : les zones de démonstration n'ont que deux élevages.
"""

# code maladie -> valeurs de la version 1 (toutes espèces)
DEMO_RULES = {
    code: {
        "lookback_days": 21,
        "lookforward_days": 0,
        "max_depth": 3,
        "min_zone_effectif": 2,
        "include_unconfirmed": True,
        "cluster_window_days": 7,
        "cluster_min_reports": 3,
        "cluster_min_ratio": None,
        "escalation_hours": 24,
    }
    for code in ("fmd", "lsd", "cbpp", "ppr", "trypanosomosis", "brucellosis", "asf",
                 "avian_influenza", "newcastle", "anthrax", "rift_valley_fever", "rabies")
}
