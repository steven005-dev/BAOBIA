import os
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User


class SeedCommandTests(TestCase):
    def test_demo_seed_is_idempotent(self):
        previous = os.environ.get("SEED_DEMO_PASSWORD")
        os.environ["SEED_DEMO_PASSWORD"] = "DemoPassword-42"
        try:
            call_command("seed", "--demo", stdout=StringIO())
            first = User.objects.count()
            call_command("seed", "--demo", stdout=StringIO())
            self.assertEqual(first, User.objects.count())
        finally:
            if previous is None:
                os.environ.pop("SEED_DEMO_PASSWORD", None)
            else:
                os.environ["SEED_DEMO_PASSWORD"] = previous
