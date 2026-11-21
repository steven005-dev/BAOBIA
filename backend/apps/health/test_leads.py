"""Pistes de maladie (apps/health/leads.py) : règles explicables, réservées aux professionnels."""

from .models import Disease, Symptom
from .test_api import HealthApiTestCase


class DiseaseLeadTests(HealthApiTestCase):
    def setUp(self):
        super().setUp()
        for code, label in (("mouth_drool", "Bave, plaies dans la bouche"),
                            ("lameness", "Boite, marche mal"), ("skin_lesions", "Boutons sur la peau")):
            Symptom.objects.create(code=code, label_fr=label).species.add(self.cattle)
        Disease.objects.create(code="asf", label_fr="Peste porcine africaine")  # porc seulement
        Disease.objects.create(code="lsd", label_fr="Dermatose nodulaire contagieuse")

    def leads(self, **overrides):
        report_id = self.submit(**overrides).json()["id"]
        data = self.as_user(self.vet).get(f"/api/health-reports/{report_id}/").json()
        return {lead["disease"]["code"]: lead for lead in data["leads"]["items"]}, data

    def test_fmd_is_a_strong_lead_with_its_explanation(self):
        leads, data = self.leads(symptom_codes=["mouth_drool", "lameness", "fever"], dead_count=0)
        fmd = leads["fmd"]
        self.assertEqual((fmd["strength"], fmd["major_found"], fmd["major_total"]), ("strong", 3, 3))
        self.assertTrue(any("cohérent" in line for line in fmd["explanation"]))
        self.assertTrue(fmd["samples"])
        self.assertEqual(list(leads)[0], "fmd")  # la plus forte d'abord
        self.assertFalse(data["leads"]["validated"])  # fiches à valider : c'est dit
        self.assertIn("pas un diagnostic", data["leads"]["warning"])

    def test_disease_of_another_species_is_never_proposed(self):
        leads, _ = self.leads(symptom_codes=["fever", "skin_lesions"])
        self.assertNotIn("asf", leads)  # bovin : la peste porcine n'est pas une piste
        self.assertIn("lsd", leads)

    def test_unusual_mortality_lowers_the_lead(self):
        leads, _ = self.leads(symptom_codes=["mouth_drool", "lameness", "fever"],
                              affected_count=4, dead_count=3)
        self.assertEqual(leads["fmd"]["strength"], "medium")  # beaucoup de morts : inhabituel
        self.assertTrue(any("inhabituel" in line for line in leads["fmd"]["explanation"]))

    def test_no_sign_of_the_profile_no_lead(self):
        leads, _ = self.leads(symptom_codes=["skin_lesions"])
        self.assertNotIn("fmd", leads)

    def test_breeder_never_sees_leads_or_label_codes(self):
        report_id = self.submit(symptom_codes=["fever"]).json()["id"]
        data = self.as_user(self.breeder).get(f"/api/health-reports/{report_id}/").json()
        self.assertNotIn("leads", data)
        self.assertNotIn("code", data["subjects"][0])


class DiseaseProfileCatalogTests(HealthApiTestCase):
    """Les 12 fiches (docs/fiches_maladies_animales_CI.txt) sont cohérentes avec le catalogue."""

    def test_every_disease_has_a_profile_a_rule_and_known_signs(self):
        from apps.alerts.catalog import DEMO_RULES

        from . import catalog
        from .disease_profiles import PROFILES

        codes = {code for code, *_ in catalog.DISEASES}
        symptoms = {code for code, *_ in catalog.SYMPTOMS}
        self.assertEqual(len(codes), 12)
        self.assertEqual(set(PROFILES), codes)
        self.assertEqual(set(DEMO_RULES), codes)  # sinon la validation échoue : « Aucune règle »
        for code, profile in PROFILES.items():
            self.assertTrue(set(profile["major"] + profile["suggestive"]) <= symptoms, code)
            species = dict((c, s) for c, _l, s in catalog.DISEASES)[code]
            self.assertEqual(set(profile["species"]), set(species), code)

    def test_anthrax_lead_carries_its_caution(self):
        Symptom.objects.create(code="sudden_death", label_fr="Mort soudaine").species.add(self.cattle)
        Disease.objects.create(code="anthrax", label_fr="Charbon bactéridien")
        report_id = self.submit(symptom_codes=["sudden_death", "fever"], affected_count=3,
                                dead_count=2).json()["id"]
        data = self.as_user(self.vet).get(f"/api/health-reports/{report_id}/").json()
        leads = {lead["disease"]["code"]: lead for lead in data["leads"]["items"]}
        self.assertEqual(leads["anthrax"]["strength"], "strong")
        self.assertIn("NE PAS OUVRIR LA CARCASSE", leads["anthrax"]["caution"])
        self.assertEqual(data["leads"]["diseases_count"], 12)
        self.assertTrue(data["leads"]["general_alert"])
