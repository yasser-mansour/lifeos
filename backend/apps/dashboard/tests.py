from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.finance.models import Account


class HomeFinancePanelTests(TestCase):
    """Regression: Home used to give Safe to Spend a prominent line even
    though it's effectively a duplicate of Personal balance in normal use
    (spec: "No giant Safe-to-Spend primary card"). Total now leads instead."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_home_shows_total_not_safe_to_spend(self):
        Account.objects.create(name="Personal Acc", context="personal", opening_balance=Decimal("9070"))
        Account.objects.create(name="Business Acc", context="business", opening_balance=Decimal("14730"))
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "23,800.00")
        self.assertNotContains(response, "Safe to spend")

    def test_home_renders_with_no_accounts(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "No accounts yet")
