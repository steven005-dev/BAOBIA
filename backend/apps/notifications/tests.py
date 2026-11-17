"""notifications et accounts.vets_for_zone. Données simulées."""

import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import services as accounts_services
from apps.accounts.tests.helpers import give_role, make_habilitation, make_user
from apps.geo.models import Zone
from apps.notifications import services
from apps.notifications.models import Notification


def zones():
    country = Zone.objects.create(level=0, code="T-CI", name="Pays test")
    region = Zone.objects.create(level=1, code="T-REG", name="Région test", parent=country)
    dep = Zone.objects.create(level=2, code="T-DEP", name="Département test", parent=region)
    other = Zone.objects.create(level=1, code="T-AUTRE", name="Autre région", parent=country)
    return country, region, dep, other


class VetsForZoneTests(TestCase):
    def setUp(self):
        self.country, self.region, self.dep, self.other = zones()
        self.verifier = make_user("+2250000000300", "Vérificateur")

    def vet(self, phone, zone, *, habilitation="verified", **role):
        user = make_user(phone, f"Vétérinaire {phone[-2:]}")
        give_role(user, "veterinarian", zone=zone, **role)
        if habilitation:
            make_habilitation(user, status=habilitation, verifier=self.verifier, ref=f"H-{phone}")
        return user

    def test_zone_and_parents_with_valid_habilitation_only(self):
        local = self.vet("+2250000000301", self.dep)
        regional = self.vet("+2250000000302", self.region)
        self.vet("+2250000000303", self.other)                      # autre région
        self.vet("+2250000000304", self.dep, habilitation="pending")  # pas habilité
        self.vet("+2250000000305", self.dep, habilitation=None)       # aucune habilitation
        self.vet("+2250000000306", None)                              # rôle sans zone
        ended = self.vet("+2250000000307", self.dep, starts_at=timezone.now() - timedelta(days=9),
                         ends_at=timezone.now() - timedelta(days=1))

        found = accounts_services.vets_for_zone(self.dep.id)
        self.assertEqual({u.id for u in found}, {local.id, regional.id})
        self.assertNotIn(ended, found)

        only_here = accounts_services.vets_for_zone(self.dep.id, include_ancestors=False)
        self.assertEqual([u.id for u in only_here], [local.id])

        # Relance au niveau au-dessus : on appelle avec la zone parente.
        self.assertEqual([u.id for u in accounts_services.vets_for_zone(self.region.id)], [regional.id])

    def test_authorities_for_zone(self):
        authority = make_user("+2250000000308", "Autorité")
        give_role(authority, "authority", zone=self.country)
        self.assertEqual([u.id for u in accounts_services.authorities_for_zone(self.dep.id)], [authority.id])


class NotifyTests(TestCase):
    def setUp(self):
        self.user = make_user("+2250000000310", "Éleveur")

    def test_unknown_code_and_forbidden_params_refused(self):
        with self.assertRaises(services.NotificationError):
            services.notify(self.user, "message.inconnu")
        with self.assertRaises(services.NotificationError):
            services.notify(self.user, "exposure.contact_possible", params={"center_name": "Élevage A"})
        with self.assertRaises(services.NotificationError):
            services.notify(self.user, "alert.validated", params={"species": {"id": 1}})
        self.assertEqual(Notification.objects.count(), 0)

    def test_in_app_is_sent_and_dedup_is_idempotent(self):
        first = services.notify(self.user, "exposure.contact_possible", dedup_key="k1")
        again = services.notify(self.user, "exposure.contact_possible", dedup_key="k1")
        self.assertEqual(first.pk, again.pk)
        self.assertEqual((first.status, first.kind), ("sent", "exposure"))
        self.assertIsNotNone(first.sent_at)
        sms = services.notify(self.user, "exposure.contact_possible", channel="sms")
        self.assertEqual(sms.status, "pending")

    def test_database_checks(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Notification.objects.create(user=self.user, kind="x", message_code="x", channel="fax")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Notification.objects.create(user=self.user, kind="x", message_code="x", status="lost")

    def test_notify_zone_vets_once_per_round(self):
        _, _, dep, _ = zones()
        verifier = make_user("+2250000000311", "Vérificateur")
        vet = make_user("+2250000000312", "Vétérinaire")
        give_role(vet, "veterinarian", zone=dep)
        make_habilitation(vet, verifier=verifier)
        alert_id = uuid.uuid4()
        params = {"species": "cattle", "reports": 4, "zone": dep.name}

        sent = services.notify_zone_vets(dep.id, "zone_cluster.review_requested", alert_id=alert_id, params=params)
        services.notify_zone_vets(dep.id, "zone_cluster.review_requested", alert_id=alert_id, params=params)
        self.assertEqual(len(sent), 1)
        self.assertEqual(Notification.objects.filter(user=vet).count(), 1)

        services.notify_zone_vets(dep.id, "zone_cluster.escalated", alert_id=alert_id, round_no=1, params=params)
        self.assertEqual(Notification.objects.filter(user=vet).count(), 2)

        nobody = Zone.objects.create(level=1, code="T-VIDE", name="Zone vide")
        self.assertEqual(
            services.notify_zone_vets(nobody.id, "zone_cluster.review_requested", alert_id=alert_id), []
        )


class NotificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.me = make_user("+2250000000320", "Moi")
        self.other = make_user("+2250000000321", "Autre")
        self.mine = [services.notify(self.me, "exposure.contact_possible") for _ in range(2)]
        self.theirs = services.notify(self.other, "exposure.contact_possible")
        self.client.force_authenticate(self.me)

    def test_list_and_count_only_mine(self):
        resp = self.client.get("/api/notifications/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({n["id"] for n in resp.json()}, {str(n.id) for n in self.mine})
        self.assertEqual(self.client.get("/api/notifications/unread-count/").json(), {"unread": 2})

    def test_mark_read_never_touches_others(self):
        resp = self.client.post(
            "/api/notifications/read/", {"ids": [str(self.mine[0].id), str(self.theirs.id)]}, format="json"
        )
        self.assertEqual(resp.json(), {"marked": 1})
        self.theirs.refresh_from_db()
        self.assertIsNone(self.theirs.read_at)
        self.assertEqual(self.client.post("/api/notifications/read/", {}, format="json").json(), {"marked": 1})
        self.assertEqual(self.client.get("/api/notifications/unread-count/").json(), {"unread": 0})

    def test_anonymous_refused(self):
        self.assertEqual(APIClient().get("/api/notifications/").status_code, 401)
