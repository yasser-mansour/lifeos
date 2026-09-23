from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.projects.models import Project
from apps.tasks.models import Task


class SearchApiTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_query_returns_quick_actions(self):
        response = self.client.get(reverse("search:api"))
        data = response.json()
        self.assertEqual(data["groups"][0]["label"], "Quick actions")

    def test_search_finds_task_and_project_by_name(self):
        Task.objects.create(title="Fix SMS callback")
        Project.objects.create(name="Northstar")
        response = self.client.get(reverse("search:api"), {"q": "Northstar"})
        data = response.json()
        labels = [g["label"] for g in data["groups"]]
        self.assertIn("Projects", labels)

    def test_search_grouped_by_type(self):
        Task.objects.create(title="Same Name Test")
        response = self.client.get(reverse("search:api"), {"q": "Same Name"})
        data = response.json()
        self.assertTrue(all("items" in g for g in data["groups"]))
