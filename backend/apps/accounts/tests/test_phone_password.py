"""Validateur unique du téléphone et règles de mot de passe."""

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.validators import normalize_phone, validate_phone


class PhoneTests(TestCase):
    def test_normalizes_common_formats_to_e164(self):
        for raw in ("+2250707070707", "+225 07 07 07 07 07", "07 07 07 07 07", "07.07.07.07.07",
                    "002250707070707", "2250707070707", "(+225) 0707-070707"):
            self.assertEqual(normalize_phone(raw), "+2250707070707", raw)

    def test_rejects_invalid_numbers(self):
        for raw in ("", "abc", "12", "+0123456789", "+22507070707070707", None):
            with self.assertRaises(ValidationError, msg=raw):
                normalize_phone(raw)

    def test_field_validator_requires_canonical_form(self):
        validate_phone("+2250707070707")
        with self.assertRaises(ValidationError):
            validate_phone("07 07 07 07 07")

    def test_user_manager_stores_e164(self):
        user = User.objects.create_user("07 07 07 07 07", "Baobia-test-2026", full_name="Test")
        self.assertEqual(user.phone, "+2250707070707")


class PasswordRulesTests(TestCase):
    def setUp(self):
        self.user = User(phone="+2250707070707", full_name="Awa Test")

    def test_digits_only_password_is_allowed(self):
        password_validation.validate_password("48271593", self.user)

    def test_too_short_common_or_phone_like_passwords_are_refused(self):
        for password in ("4827159", "12345678", "password", "2250707070707"):
            with self.assertRaises(ValidationError, msg=password):
                password_validation.validate_password(password, self.user)
