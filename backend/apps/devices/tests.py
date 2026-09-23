import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Profile
from apps.devices.models import Device, DeviceCredential, PairingToken, SyncConflict
from apps.finance.models import Account, Transaction
from apps.journal.models import JournalEntry
from apps.writing.models import Book, Chapter


class PairingTokenTests(TestCase):
    def test_freshly_issued_token_is_valid(self):
        token = PairingToken.issue()
        self.assertTrue(token.is_valid)

    def test_expired_token_is_invalid(self):
        token = PairingToken.issue()
        token.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        token.save()
        self.assertFalse(token.is_valid)

    def test_consumed_token_is_single_use(self):
        token = PairingToken.issue()
        device = Device.objects.create(name="Phone", platform="android")
        token.consume(device)
        self.assertFalse(token.is_valid)
        self.assertEqual(token.used_by_device, device)


class DeviceCredentialTests(TestCase):
    def test_issue_and_authenticate_round_trip(self):
        device = Device.objects.create(name="Phone", platform="android")
        raw_token = DeviceCredential.issue(device)
        found = DeviceCredential.authenticate(raw_token)
        self.assertEqual(found, device)

    def test_wrong_token_does_not_authenticate(self):
        device = Device.objects.create(name="Phone", platform="android")
        DeviceCredential.issue(device)
        self.assertIsNone(DeviceCredential.authenticate("not-the-real-token"))

    def test_revoked_device_cannot_authenticate(self):
        device = Device.objects.create(name="Phone", platform="android")
        raw_token = DeviceCredential.issue(device)
        device.revoke()
        self.assertIsNone(DeviceCredential.authenticate(raw_token))

    def test_reissuing_credential_invalidates_old_token(self):
        device = Device.objects.create(name="Phone", platform="android")
        old_token = DeviceCredential.issue(device)
        new_token = DeviceCredential.issue(device)
        self.assertIsNone(DeviceCredential.authenticate(old_token))
        self.assertEqual(DeviceCredential.authenticate(new_token), device)


class ClaimDeviceApiTests(TestCase):
    def test_claim_with_valid_token_issues_credential(self):
        pairing_token = PairingToken.issue()
        response = self.client.post(
            reverse("device-claim"),
            {"pairing_token": pairing_token.token, "device_name": "Galaxy A25", "platform": "android"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("device_token", response.json())
        self.assertTrue(Device.objects.filter(name="Galaxy A25").exists())

    def test_claim_with_invalid_token_rejected(self):
        response = self.client.post(reverse("device-claim"), {"pairing_token": "bogus", "device_name": "X"})
        self.assertEqual(response.status_code, 400)

    def test_claim_token_cannot_be_reused(self):
        pairing_token = PairingToken.issue()
        payload = {"pairing_token": pairing_token.token, "device_name": "Phone One"}
        first = self.client.post(reverse("device-claim"), payload)
        second = self.client.post(reverse("device-claim"), {**payload, "device_name": "Phone Two"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)


class DeviceViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_state(self):
        response = self.client.get(reverse("devices:list"))
        self.assertContains(response, "No devices paired yet")

    def test_pair_page_renders_qr(self):
        response = self.client.get(reverse("devices:pair"))
        self.assertContains(response, "data:image/png;base64,")

    def test_pair_page_shows_manual_fallback_matching_the_qr_token(self):
        """Regression: for a while the pairing token only ever existed
        inside the QR image — a phone that couldn't use its camera had no
        way to pair at all. The same host/port/token must also be readable
        as plain text so the Android app's manual-entry fallback can use it."""
        response = self.client.get(reverse("devices:pair"))
        pairing_token = PairingToken.objects.latest("created_at")
        self.assertContains(response, pairing_token.token)
        self.assertContains(response, "8420")

    def test_revoke_device(self):
        device = Device.objects.create(name="Old Phone", platform="android", device_type="mobile")
        self.client.post(reverse("devices:revoke", args=[device.pk]))
        device.refresh_from_db()
        self.assertTrue(device.revoked)
        self.assertNotContains(self.client.get(reverse("devices:list")), "Old Phone")


class ConflictDetectionApiTests(TestCase):
    """A device (Android) pushing a stale update — one based on a version
    older than what's currently on the Mac — must not silently overwrite
    the newer Mac record. It should be parked as a SyncConflict instead.
    Desktop (session-authenticated) edits are a different, synchronous path
    and must never be affected by this at all."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=self.owner, display_name="Owner")
        self.device = Device.objects.create(name="Phone", platform="android", device_type="mobile")
        raw_token = DeviceCredential.issue(self.device)
        self.device_headers = {"HTTP_AUTHORIZATION": f"Device {raw_token}"}

    def _patch(self, url, data, **extra):
        return self.client.patch(url, data=json.dumps(data), content_type="application/json", **extra)

    def test_stale_device_push_is_parked_as_conflict_not_applied(self):
        entry = JournalEntry.objects.create(title="Original", body="first draft")
        entry.title = "Edited on Mac"
        entry.save()
        self.assertEqual(entry.version, 2)

        response = self._patch(
            reverse("journalentry-detail", args=[entry.pk]),
            {"title": "Edited on phone", "version": 1},
            **self.device_headers,
        )

        self.assertEqual(response.status_code, 409)
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Edited on Mac")
        conflict = SyncConflict.objects.get()
        self.assertEqual(conflict.entity_type, "journal_entry")
        self.assertEqual(conflict.entity_id, entry.id)
        self.assertEqual(conflict.device, self.device)
        self.assertEqual(conflict.status, "pending")
        self.assertEqual(conflict.server_version, 2)
        self.assertEqual(conflict.local_version, 1)
        self.assertEqual(conflict.local_data["title"], "Edited on phone")

    def test_device_push_at_current_version_applies_normally(self):
        entry = JournalEntry.objects.create(title="Original")
        response = self._patch(
            reverse("journalentry-detail", args=[entry.pk]),
            {"title": "Updated from phone", "version": entry.version},
            **self.device_headers,
        )
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Updated from phone")
        self.assertFalse(SyncConflict.objects.exists())

    def test_device_push_without_version_is_unchecked_for_backward_compatibility(self):
        entry = JournalEntry.objects.create(title="Original")
        entry.title = "Edited on Mac"
        entry.save()
        response = self._patch(reverse("journalentry-detail", args=[entry.pk]), {"title": "No version field"}, **self.device_headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SyncConflict.objects.exists())

    def test_desktop_edit_is_never_treated_as_a_device_conflict(self):
        entry = JournalEntry.objects.create(title="Original")
        entry.title = "Edited elsewhere"
        entry.save()
        self.client.login(username="owner", password="testpass123")
        response = self._patch(reverse("journalentry-detail", args=[entry.pk]), {"title": "Desktop edit", "version": 1})
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Desktop edit")
        self.assertFalse(SyncConflict.objects.exists())

    def test_transaction_conflict(self):
        account = Account.objects.create(name="Cash", context="personal", account_type="cash", opening_balance=Decimal("100.00"))
        txn = Transaction.objects.create(account=account, amount=Decimal("50.00"), type="expense", direction="out", date=timezone.now().date())
        txn.description = "Edited on Mac"
        txn.save()

        response = self._patch(
            reverse("transaction-detail", args=[txn.pk]),
            {"description": "Edited on phone", "version": 1},
            **self.device_headers,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(SyncConflict.objects.get().entity_type, "transaction")

    def test_chapter_conflict(self):
        book = Book.objects.create(title="My Book")
        chapter = Chapter.objects.create(book=book, title="One", content="one two three")
        chapter.content = "edited on Mac"
        chapter.save()

        response = self._patch(
            reverse("chapter-detail", args=[chapter.pk]),
            {"content": "edited on phone", "version": 1},
            **self.device_headers,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(SyncConflict.objects.get().entity_type, "chapter")

    def test_study_session_correction_conflict(self):
        from apps.study import services

        session = services.start_session(mode="stopwatch")
        session.correction_reason = "corrected on Mac"
        session.save()

        response = self._patch(
            reverse("studysession-detail", args=[session.pk]),
            {"corrected_duration_seconds": 600, "correction_reason": "corrected on phone", "version": 1},
            **self.device_headers,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(SyncConflict.objects.get().entity_type, "study_session")


class ConflictResolutionViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=self.owner, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.device = Device.objects.create(name="Phone", platform="android", device_type="mobile")
        self.entry = JournalEntry.objects.create(title="On the Mac", body="mac body")
        self.entry.title = "Still on the Mac"
        self.entry.save()  # version 2
        self.conflict = SyncConflict.objects.create(
            entity_type="journal_entry", entity_id=self.entry.id, device=self.device,
            local_data={"title": "From the phone", "body": "phone body"},
            server_version=2, local_version=1,
        )

    def test_conflicts_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("devices:conflicts"))
        self.assertNotEqual(response.status_code, 200)

    def test_conflicts_page_lists_pending_conflict(self):
        response = self.client.get(reverse("devices:conflicts"))
        self.assertContains(response, "Still on the Mac")
        self.assertContains(response, "From the phone")

    def test_settings_sidebar_shows_conflict_badge(self):
        response = self.client.get(reverse("core:settings_section", args=["general"]))
        self.assertContains(response, ">1<")

    def test_keep_mac_discards_device_data(self):
        self.client.post(reverse("devices:conflict_resolve", args=[self.conflict.pk]), {"action": "keep_mac"})
        self.entry.refresh_from_db()
        self.conflict.refresh_from_db()
        self.assertEqual(self.entry.title, "Still on the Mac")
        self.assertEqual(self.conflict.status, "resolved_server")
        self.assertIsNotNone(self.conflict.resolved_at)

    def test_keep_local_applies_device_data_over_mac_record(self):
        self.client.post(reverse("devices:conflict_resolve", args=[self.conflict.pk]), {"action": "keep_local"})
        self.entry.refresh_from_db()
        self.conflict.refresh_from_db()
        self.assertEqual(self.entry.title, "From the phone")
        self.assertEqual(self.entry.body, "phone body")
        self.assertEqual(self.conflict.status, "resolved_local")

    def test_keep_both_creates_a_new_record_and_leaves_original_untouched(self):
        before = JournalEntry.objects.count()
        self.client.post(reverse("devices:conflict_resolve", args=[self.conflict.pk]), {"action": "keep_both"})
        self.entry.refresh_from_db()
        self.conflict.refresh_from_db()
        self.assertEqual(self.entry.title, "Still on the Mac")  # untouched
        self.assertEqual(JournalEntry.objects.count(), before + 1)
        self.assertTrue(JournalEntry.objects.filter(title="From the phone").exists())
        self.assertEqual(self.conflict.status, "resolved_both")

    def test_resolved_conflict_no_longer_listed(self):
        self.client.post(reverse("devices:conflict_resolve", args=[self.conflict.pk]), {"action": "keep_mac"})
        response = self.client.get(reverse("devices:conflicts"))
        self.assertContains(response, "No conflicts")
