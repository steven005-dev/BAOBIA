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
