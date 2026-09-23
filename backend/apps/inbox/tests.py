from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.inbox.models import InboxItem
from apps.tasks.models import Task


class InboxViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_state(self):
        response = self.client.get(reverse("inbox:list"))
        self.assertContains(response, "Inbox zero")

    def test_capture_creates_item(self):
        self.client.post(reverse("inbox:capture"), {"content": "Call client tomorrow"})
        self.assertTrue(InboxItem.objects.filter(content="Call client tomorrow").exists())

    def test_convert_to_task(self):
        item = InboxItem.objects.create(content="Buy invoices software")
        self.client.post(reverse("inbox:to_task", args=[item.pk]))
        item.refresh_from_db()
        self.assertTrue(item.processed)
        self.assertEqual(item.converted_to, "task")
        self.assertTrue(Task.objects.filter(title="Buy invoices software").exists())

    def test_dismiss_marks_processed(self):
        item = InboxItem.objects.create(content="Random thought")
        self.client.post(reverse("inbox:dismiss", args=[item.pk]))
        item.refresh_from_db()
        self.assertTrue(item.processed)
