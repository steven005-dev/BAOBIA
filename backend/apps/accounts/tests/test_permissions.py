"""Permissions réutilisables et fonctions publiques de accounts.services."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.models import Habilitation, Mandate
from apps.accounts.permissions import HasCenterAccess, HasRole, HasValidHabilitation
from apps.audit.models import AuditLog
from apps.identity import services as identity_services

from .helpers import give_role, make_center, make_habilitation, make_user, role

factory = APIRequestFactory()


def call(permissions, user, url="/x/", method="get", data=None, view_attrs=None, **kwargs):
    """Appelle une vraie vue DRF protégée par `permissions` et retourne le code HTTP."""
    attrs = {"permission_classes": permissions,
             "get": lambda self, request, **kw: Response({"ok": True}),
             "post": lambda self, request, **kw: Response({"ok": True})}
    attrs.update(view_attrs or {})
    view = type("ProbeView", (APIView,), attrs).as_view()
    request = getattr(factory, method)(url, data or {}, format="json")
    if user is not None:
        force_authenticate(request, user=user)
    return view(request, **kwargs)


class HabilitationTests(TestCase):
    def setUp(self):
        self.vet = make_user("+2250000000051", "Vétérinaire")
        self.verifier = make_user("+2250000000052", "Autorité")

    def assertRefused(self):
        self.assertFalse(services.user_has_valid_habilitation(self.vet))
        response = call([HasValidHabilitation], self.vet)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Votre habilitation n'est pas valide.")

    def test_valid_verified_habilitation_is_accepted(self):
        hab = make_habilitation(self.vet, verifier=self.verifier)
        self.assertEqual(call([HasValidHabilitation], self.vet).status_code, 200)
        self.assertEqual(services.get_valid_habilitation(self.vet), hab)

    def test_expired_by_date_is_refused(self):
        make_habilitation(self.vet, verifier=self.verifier, days_from=-30, days_to=-1)
        self.assertRefused()

    def test_status_expired_is_refused(self):
        make_habilitation(self.vet, status="expired")
        self.assertRefused()

    def test_revoked_is_refused(self):
        make_habilitation(self.vet, status="revoked")
        self.assertRefused()

    def test_not_verified_is_refused(self):
        make_habilitation(self.vet, status="pending")
        self.assertRefused()

    def test_not_yet_valid_is_refused(self):
        make_habilitation(self.vet, verifier=self.verifier, days_from=2, days_to=30)
        self.assertRefused()

    def test_inactive_account_is_refused(self):
        make_habilitation(self.vet, verifier=self.verifier)
        self.vet.is_active = False
        self.vet.save(update_fields=["is_active"])
        self.assertFalse(services.user_has_valid_habilitation(self.vet))

    def test_validity_at_a_given_date(self):
        make_habilitation(self.vet, verifier=self.verifier, days_from=-30, days_to=-10)
        today = timezone.localdate()
        self.assertTrue(services.user_has_valid_habilitation(self.vet, at=today - timedelta(days=20)))
        self.assertTrue(services.user_has_valid_habilitation(
            self.vet, at=timezone.now() - timedelta(days=15)))
        self.assertFalse(services.user_has_valid_habilitation(self.vet, at=today))

    def test_verify_habilitation_is_audited_and_refuses_self(self):
        hab = make_habilitation(self.vet, status="pending")
        with self.assertRaises(services.AccountsError):
            services.verify_habilitation(hab, self.vet)
        services.verify_habilitation(hab, self.verifier)
        hab.refresh_from_db()
        self.assertEqual((hab.status, hab.verified_by), ("verified", self.verifier))
        entry = AuditLog.objects.get(action="habilitation.verify")
        self.assertEqual((entry.actor_user, entry.entity_id), (self.verifier, hab.id))
        self.assertTrue(services.user_has_valid_habilitation(self.vet))

    def test_revoked_cannot_be_verified(self):
        hab = make_habilitation(self.vet, status="revoked")
        with self.assertRaises(services.AccountsError):
            services.verify_habilitation(hab, self.verifier)
        self.assertEqual(Habilitation.objects.get(pk=hab.pk).status, "revoked")


class RoleTests(TestCase):
    def setUp(self):
        self.user = make_user("+2250000000061")

    def test_active_role(self):
        give_role(self.user, "veterinarian")
        self.assertTrue(services.user_has_role(self.user, "veterinarian"))
        self.assertEqual(call([HasRole("veterinarian")], self.user).status_code, 200)
        self.assertEqual(call([HasRole("authority", "veterinarian")], self.user).status_code, 200)
        self.assertEqual(call([HasRole("authority")], self.user).status_code, 403)

    def test_ended_and_future_roles_do_not_count(self):
        now = timezone.now()
        give_role(self.user, "veterinarian", starts_at=now - timedelta(days=5), ends_at=now - timedelta(days=1))
        give_role(self.user, "authority", starts_at=now + timedelta(days=1))
        self.assertEqual(services.active_roles(self.user), [])
        self.assertEqual(call([HasRole("veterinarian")], self.user).status_code, 403)

    def test_role_at_a_past_date(self):
        now = timezone.now()
        give_role(self.user, "breeder", starts_at=now - timedelta(days=5), ends_at=now - timedelta(days=1))
        self.assertTrue(services.user_has_role(self.user, "breeder", at=now - timedelta(days=3)))

    def test_anonymous_is_refused(self):
        self.assertEqual(call([HasRole("breeder")], None).status_code, 401)

    def test_grant_role_is_idempotent(self):
        role("breeder")
        first = services.grant_role(self.user, "breeder")
        self.assertEqual(services.grant_role(self.user, "breeder"), first)
        self.assertEqual(AuditLog.objects.filter(action="role.grant").count(), 1)


class CenterAccessTests(TestCase):
    def setUp(self):
        self.holder = make_user("+2250000000071", "Détenteur")
        self.agent = make_user("+2250000000072", "Agent")
        self.stranger = make_user("+2250000000073", "Inconnu")
        self.center = make_center(self.holder, name="Élevage 1")
        self.other_center = make_center(self.holder, name="Élevage 2")

    def status(self, user, center_id, permission=HasCenterAccess, **kwargs):
        return call([permission], user, url=f"/c/{center_id}/", center_id=str(center_id), **kwargs).status_code

    def test_member_has_access_others_do_not(self):
        self.assertEqual(self.status(self.holder, self.center.id), 200)
        response = call([HasCenterAccess], self.stranger, center_id=str(self.center.id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Vous n'avez pas accès à cet élevage.")

    def test_center_id_from_body_or_query(self):
        self.assertEqual(call([HasCenterAccess], self.holder, method="post",
                              data={"center_id": str(self.center.id)}).status_code, 200)
        self.assertEqual(call([HasCenterAccess], self.holder,
                              url=f"/x/?center_id={self.center.id}").status_code, 200)
        self.assertEqual(call([HasCenterAccess], self.holder).status_code, 403)  # pas de centre

    def test_mandate_covers_only_its_centers_and_scope(self):
        identity_services.grant_mandate(self.agent, self.holder, [self.center], "declare")
        self.assertEqual(self.status(self.agent, self.center.id), 200)
        self.assertEqual(self.status(self.agent, self.other_center.id), 403)
        self.assertEqual(self.status(self.agent, self.center.id, HasCenterAccess.for_scope("declare")), 200)
        self.assertEqual(self.status(self.agent, self.center.id, HasCenterAccess.for_scope("move")), 403)

    def test_revoked_ended_or_future_mandate_gives_no_access(self):
        now = timezone.now()
        for values in ({"revoked_at": now},
                       {"starts_at": now - timedelta(days=5), "ends_at": now - timedelta(days=1)},
                       {"starts_at": now + timedelta(days=1)}):
            mandate = identity_services.grant_mandate(self.agent, self.holder, [self.center], "all")
            Mandate.objects.filter(pk=mandate.pk).update(**values)
            self.assertEqual(self.status(self.agent, self.center.id), 403, values)
            # On neutralise ce mandat pour le cas suivant (jamais de suppression).
            Mandate.objects.filter(pk=mandate.pk).update(revoked_at=now)

    def test_object_permission(self):
        unit = type("Unit", (), {"current_center_id": self.center.id})()
        permission = HasCenterAccess()
        request = type("Req", (), {"user": self.holder})()
        self.assertTrue(permission.has_object_permission(request, None, self.center))
        self.assertTrue(permission.has_object_permission(request, None, unit))
        request.user = self.stranger
        self.assertFalse(permission.has_object_permission(request, None, unit))

    def test_center_from_object_defers_to_object_check(self):
        response = call([HasCenterAccess], self.stranger, view_attrs={"center_from_object": True})
        self.assertEqual(response.status_code, 200)  # la vue doit appeler get_object()
