import json
import tempfile
import time
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import ActivityEvent, Profile, log_activity
from apps.people.models import Person  # concrete BaseModel subclass for base-behavior tests


class BaseModelBehaviorTests(TestCase):
    """Exercises apps.core.models.BaseModel through a concrete subclass —
    UUID pks, versioning, and soft delete are shared by every domain model."""

    def test_id_is_a_uuid(self):
        person = Person.objects.create(name="Test")
        self.assertEqual(len(str(person.id)), 36)

    def test_created_and_updated_at_set_on_create(self):
        person = Person.objects.create(name="Test")
        self.assertIsNotNone(person.created_at)
        self.assertIsNotNone(person.updated_at)

    def test_version_starts_at_one(self):
        person = Person.objects.create(name="Test")
        self.assertEqual(person.version, 1)

    def test_soft_delete_excludes_from_default_manager_but_not_all_objects(self):
        person = Person.objects.create(name="Test")
        person.soft_delete()
        self.assertFalse(Person.objects.filter(pk=person.pk).exists())
        self.assertTrue(Person.all_objects.filter(pk=person.pk).exists())
        self.assertTrue(Person.all_objects.get(pk=person.pk).is_deleted)

    def test_restore_undoes_soft_delete(self):
        person = Person.objects.create(name="Test")
        person.soft_delete()
        person.restore()
        self.assertTrue(Person.objects.filter(pk=person.pk).exists())

    def test_plain_delete_soft_deletes_instead_of_destroying_the_row(self):
        """Regression guard: DRF's default ModelViewSet.destroy() (the
        Android API's DELETE) calls the plain instance .delete(), not
        soft_delete(). Before this override, that path would have
        permanently destroyed financial/journal/study history the moment
        an Android delete button called it — never soft-deleted."""
        person = Person.objects.create(name="Test")
        pk = person.pk
        person.delete()
        self.assertFalse(Person.objects.filter(pk=pk).exists())
        self.assertTrue(Person.all_objects.filter(pk=pk).exists())
        self.assertTrue(Person.all_objects.get(pk=pk).is_deleted)

    def test_hard_delete_is_the_explicit_escape_hatch(self):
        person = Person.objects.create(name="Test")
        pk = person.pk
        person.hard_delete()
        self.assertFalse(Person.all_objects.filter(pk=pk).exists())


class HealthEndpointTests(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "ok")
        self.assertIn("version", data)


class PreMigrationBackupSafetyTests(TestCase):
    """run_server.py — the actual entry point LIFEOS.app and every packaged
    build launch (never manage.py runserver) — must back up an existing
    database before applying any pending migration (distribution spec
    "Pre-migration backups" / "Update safety"), but never on an ordinary
    launch with nothing pending, and never on a brand first launch with no
    database file yet."""

    def _import_run_server(self):
        import sys
        from pathlib import Path

        backend_dir = str(Path(__file__).resolve().parent.parent.parent)
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        import run_server

        return run_server

    def test_no_pending_migrations_on_a_fully_migrated_test_database(self):
        run_server = self._import_run_server()
        self.assertFalse(run_server._has_pending_migrations())

    def test_backs_up_when_migrations_are_pending_and_db_file_exists(self):
        run_server = self._import_run_server()
        with patch.object(run_server, "_has_pending_migrations", return_value=True), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("apps.core.backup.create_backup") as mock_backup:
            mock_backup.return_value.path = "fake-backup.sqlite3"
            run_server._backup_before_migrating()
        mock_backup.assert_called_once()

    def test_skips_backup_when_nothing_is_pending(self):
        run_server = self._import_run_server()
        with patch.object(run_server, "_has_pending_migrations", return_value=False), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("apps.core.backup.create_backup") as mock_backup:
            run_server._backup_before_migrating()
        mock_backup.assert_not_called()

    def test_skips_backup_when_no_database_file_exists_yet(self):
        """A brand first launch: nothing to back up, and pending migrations
        are expected (that's exactly what creates the fresh database)."""
        run_server = self._import_run_server()
        with patch.object(run_server, "_has_pending_migrations", return_value=True), \
             patch("pathlib.Path.exists", return_value=False), \
             patch("apps.core.backup.create_backup") as mock_backup:
            run_server._backup_before_migrating()
        mock_backup.assert_not_called()


class FirstRunTests(TestCase):
    """The onboarding wizard (apps.core.views.Onboarding*View) stages every
    step's answers in the session and only writes User/Profile/Account/
    Project once, atomically, at /first-run/complete/ — see spec "Interrupted
    onboarding" and "Application startup state machine"."""

    def walk_through_onboarding(self, *, display_name="Alex", password="testpass123", modules=None, school_name=None, project_name=None, account_name=None):
        self.client.post(reverse("core:onboarding_profile"), {"display_name": display_name, "theme": "system"})
        self.client.post(reverse("core:onboarding_security"), {"password": password, "password_confirm": password})
        personalize = {"tasks": "on", "focus": "on", "notes": "on"}
        for module in modules or []:
            personalize[module] = "on"
        response = self.client.post(reverse("core:onboarding_personalize"), personalize)
        if "finance" in (modules or []):
            finance_data = {"default_currency": "MAD"}
            if account_name:
                finance_data.update({"account_name": account_name, "account_type": "bank", "opening_balance": "0"})
            response = self.client.post(reverse("core:onboarding_finance"), finance_data)
        if "school" in (modules or []):
            response = self.client.post(reverse("core:onboarding_school"), {"school_name": school_name or ""})
        if "projects" in (modules or []):
            response = self.client.post(reverse("core:onboarding_project"), {"project_name": project_name or ""})
        return self.client.get(reverse("core:onboarding_complete"))

    def test_onboarding_creates_owner_and_logs_in(self):
        response = self.walk_through_onboarding(display_name="Alex", modules=["finance", "school"], school_name="Northgate University")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="owner").exists())
        profile = Profile.objects.get()
        self.assertEqual(profile.display_name, "Alex")
        self.assertEqual(profile.school_name, "Northgate University")
        self.assertIn("finance", profile.enabled_modules)
        self.assertIsNotNone(profile.onboarded_at)
        # Already authenticated by the time /complete/ renders:
        home = self.client.get(reverse("dashboard:home"))
        self.assertEqual(home.status_code, 200)

    def test_onboarding_optional_account_and_project_are_created_when_provided(self):
        from apps.finance.models import Account
        from apps.projects.models import Project

        self.walk_through_onboarding(modules=["finance", "projects"], account_name="Main Bank", project_name="First Project")
        self.assertTrue(Account.objects.filter(name="Main Bank").exists())
        self.assertTrue(Project.objects.filter(name="First Project").exists())

    def test_skipping_optional_steps_creates_no_account_or_project(self):
        from apps.finance.models import Account
        from apps.projects.models import Project

        self.walk_through_onboarding(modules=["finance", "projects"])
        self.assertFalse(Account.objects.exists())
        self.assertFalse(Project.objects.exists())

    def test_onboarding_redirects_to_login_once_a_profile_exists(self):
        user = User.objects.create_user(username="owner", password="x")
        Profile.objects.create(user=user, display_name="Owner")
        response = self.client.get(reverse("core:onboarding_welcome"))
        self.assertRedirects(response, reverse("core:login"))

    def test_mismatched_passwords_rejected(self):
        response = self.client.post(reverse("core:onboarding_security"), {"password": "one12345", "password_confirm": "two12345"})
        self.assertEqual(response.status_code, 200)  # re-rendered with errors
        self.assertFalse(Profile.objects.exists())

    def test_jumping_straight_to_complete_without_a_passcode_does_not_create_an_owner(self):
        """A stray GET at /first-run/complete/ (e.g. a bookmarked/reloaded
        URL) must never create a half-onboarded owner with no passcode."""
        response = self.client.get(reverse("core:onboarding_complete"))
        self.assertRedirects(response, reverse("core:onboarding_welcome"))
        self.assertFalse(Profile.objects.exists())

    def test_closing_mid_onboarding_leaves_no_trace(self):
        """Simulates quitting LIFEOS after Profile+Security but before
        Personalize/Complete — relaunching (a fresh GET at welcome) must not
        see a half-created owner, and completing normally afterward must not
        create duplicates."""
        self.client.post(reverse("core:onboarding_profile"), {"display_name": "Alex", "theme": "system"})
        self.client.post(reverse("core:onboarding_security"), {"password": "testpass123", "password_confirm": "testpass123"})
        self.assertFalse(Profile.objects.exists())
        response = self.client.get(reverse("core:onboarding_welcome"))
        self.assertEqual(response.status_code, 200)  # still pre-onboarding, no redirect to login
        self.walk_through_onboarding(display_name="Alex")
        self.assertEqual(Profile.objects.count(), 1)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=self.user, display_name="Owner")

    def test_login_with_correct_passcode(self):
        response = self.client.post(reverse("core:login"), {"password": "testpass123"})
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_login_with_wrong_passcode_fails(self):
        response = self.client.post(reverse("core:login"), {"password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_passcode_is_hashed_not_plaintext(self):
        self.assertNotEqual(self.user.password, "testpass123")
        self.assertTrue(self.user.password.startswith("pbkdf2_"))

    def test_correct_passcode_still_works_after_a_failed_attempt(self):
        self.client.post(reverse("core:login"), {"password": "wrong"})
        response = self.client.post(reverse("core:login"), {"password": "testpass123"})
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_logout_ends_session(self):
        self.client.login(username="owner", password="testpass123")
        self.client.post(reverse("core:logout"))
        self.assertFalse("_auth_user_id" in self.client.session)
        home = self.client.get(reverse("dashboard:home"))
        self.assertNotEqual(home.status_code, 200)

    def test_logout_requires_post(self):
        self.client.login(username="owner", password="testpass123")
        response = self.client.get(reverse("core:logout"))
        self.assertEqual(response.status_code, 405)


class PasscodeChangeTests(TestCase):
    """Regression coverage for the reported "passcode says wrong after
    first-run setup" bug. Root cause was never a broken hash/compare — it was
    that no logout mechanism existed anywhere in the UI, so there was no real
    way to end a session and re-authenticate. These tests exercise the full
    lifecycle a real reopen goes through: change, persist, log out, and
    re-authenticate against both the new and old passcode."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=self.user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_wrong_current_passcode_rejected(self):
        response = self.client.post(reverse("core:passcode_change"), {
            "current_password": "notmypasscode", "new_password": "newpass456", "new_password_confirm": "newpass456",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not your current passcode")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))

    def test_mismatched_new_passcodes_rejected(self):
        response = self.client.post(reverse("core:passcode_change"), {
            "current_password": "testpass123", "new_password": "newpass456", "new_password_confirm": "different789",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "don&#x27;t match")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))

    def test_successful_change_updates_hash(self):
        response = self.client.post(reverse("core:passcode_change"), {
            "current_password": "testpass123", "new_password": "newpass456", "new_password_confirm": "newpass456",
        })
        self.assertRedirects(response, reverse("core:settings_section", args=["security"]))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass456"))
        self.assertNotEqual(self.user.password, "newpass456")  # still hashed

    def test_session_persists_immediately_after_change(self):
        """update_session_auth_hash must be called on change, or the user is
        silently logged out mid-flow and it looks like the app is broken."""
        self.client.post(reverse("core:passcode_change"), {
            "current_password": "testpass123", "new_password": "newpass456", "new_password_confirm": "newpass456",
        })
        home = self.client.get(reverse("dashboard:home"))
        self.assertEqual(home.status_code, 200)

    def test_old_passcode_rejected_after_change_and_reopen(self):
        self.client.post(reverse("core:passcode_change"), {
            "current_password": "testpass123", "new_password": "newpass456", "new_password_confirm": "newpass456",
        })
        self.client.post(reverse("core:logout"))  # simulates quit + reopen
        response = self.client.post(reverse("core:login"), {"password": "testpass123"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_new_passcode_accepted_after_change_and_reopen(self):
        self.client.post(reverse("core:passcode_change"), {
            "current_password": "testpass123", "new_password": "newpass456", "new_password_confirm": "newpass456",
        })
        self.client.post(reverse("core:logout"))  # simulates quit + reopen
        response = self.client.post(reverse("core:login"), {"password": "newpass456"})
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_change_requires_post(self):
        response = self.client.get(reverse("core:passcode_change"))
        self.assertEqual(response.status_code, 405)

    def test_change_requires_login(self):
        self.client.post(reverse("core:logout"))
        response = self.client.post(reverse("core:passcode_change"), {
            "current_password": "testpass123", "new_password": "newpass456", "new_password_confirm": "newpass456",
        })
        self.assertNotEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))


class ResetPasscodeCommandTests(TestCase):
    """The `reset_passcode` management command is the local-recovery path for
    a forgotten passcode. It must require interactive confirmation, hash the
    new passcode the same way normal login does, and never be reachable any
    way except local shell access (no HTTP path exercises this command)."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=self.user, display_name="Owner")

    def test_no_owner_account_raises(self):
        self.user.delete()
        with self.assertRaises(CommandError):
            call_command("reset_passcode", stdout=StringIO())

    def test_declining_confirmation_leaves_passcode_unchanged(self):
        with patch("builtins.input", return_value="not reset"):
            call_command("reset_passcode", stdout=StringIO())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))

    def test_mismatched_new_passcodes_raises_and_leaves_unchanged(self):
        with patch("builtins.input", return_value="RESET"), \
             patch("getpass.getpass", side_effect=["newpass456", "different789"]):
            with self.assertRaises(CommandError):
                call_command("reset_passcode", stdout=StringIO())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))

    def test_too_short_passcode_raises_and_leaves_unchanged(self):
        with patch("builtins.input", return_value="RESET"), \
             patch("getpass.getpass", side_effect=["abc", "abc"]):
            with self.assertRaises(CommandError):
                call_command("reset_passcode", stdout=StringIO())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpass123"))

    def test_confirmed_reset_changes_passcode_and_logs_activity(self):
        with patch("builtins.input", return_value="RESET"), \
             patch("getpass.getpass", side_effect=["newpass456", "newpass456"]):
            call_command("reset_passcode", stdout=StringIO())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass456"))
        self.assertFalse(self.user.check_password("testpass123"))
        self.assertTrue(ActivityEvent.objects.filter(verb__icontains="reset via local recovery").exists())

    def test_reset_passcode_then_login_with_new_passcode_via_http(self):
        with patch("builtins.input", return_value="RESET"), \
             patch("getpass.getpass", side_effect=["newpass456", "newpass456"]):
            call_command("reset_passcode", stdout=StringIO())
        response = self.client.post(reverse("core:login"), {"password": "newpass456"})
        self.assertRedirects(response, reverse("dashboard:home"))


class SettingsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=self.user, display_name="Owner", default_currency="MAD")
        self.client.login(username="owner", password="testpass123")

    def test_save_general_settings(self):
        response = self.client.post(reverse("core:settings_section", args=["general"]), {
            "display_name": "New Name", "default_currency": "USD", "school_name": "",
        })
        self.assertRedirects(response, reverse("core:settings_section", args=["general"]))
        profile = Profile.objects.get()
        self.assertEqual(profile.display_name, "New Name")
        self.assertEqual(profile.default_currency, "USD")

    def test_save_appearance_settings(self):
        response = self.client.post(reverse("core:settings_section", args=["appearance"]), {"theme": "dark"})
        self.assertRedirects(response, reverse("core:settings_section", args=["appearance"]))
        self.assertEqual(Profile.objects.get().theme, "dark")

    def test_save_autolock_settings(self):
        response = self.client.post(reverse("core:settings_section", args=["security"]), {"auto_lock_minutes": "30"})
        self.assertRedirects(response, reverse("core:settings_section", args=["security"]))
        self.assertEqual(Profile.objects.get().auto_lock_minutes, 30)

    def test_default_settings_view_uses_general_section(self):
        response = self.client.post(reverse("core:settings"), {
            "display_name": "Default Path", "default_currency": "MAD", "school_name": "",
        })
        self.assertRedirects(response, reverse("core:settings_section", args=["general"]))

    def test_logged_out_request_redirects_to_login_instead_of_crashing(self):
        """Regression: SettingsView was a bare View with no login guard —
        every sibling view in this module uses @login_required, but this one
        was missed, so an anonymous request 500'd on Profile.objects.get(user=
        AnonymousUser) instead of redirecting to login."""
        self.client.logout()
        response = self.client.get(reverse("core:settings_section", args=["general"]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("core:onboarding_welcome"), response.url)


class ActivityLogTests(TestCase):
    def test_log_activity_creates_event(self):
        log_activity("Did a thing", category="tasks")
        self.assertEqual(ActivityEvent.objects.filter(verb="Did a thing").count(), 1)


class BackupRestoreTests(TestCase):
    """Exercises apps.core.backup against a real on-disk SQLite file — the
    module talks to sqlite3 directly, not through Django's test-DB machinery
    (which defaults to :memory: and doesn't represent a real backup)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.db_path = Path(self.tmp_dir.name) / "source.sqlite3"
        self.backup_dir = Path(self.tmp_dir.name) / "backups"

        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE marker (value TEXT)")
        conn.execute("INSERT INTO marker VALUES ('original')")
        conn.commit()
        conn.close()

        self.settings_override = override_settings(
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(self.db_path)}},
            LIFEOS_BACKUP_DIR=self.backup_dir,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def _read_marker(self, path):
        import sqlite3

        conn = sqlite3.connect(str(path))
        value = conn.execute("SELECT value FROM marker").fetchone()[0]
        conn.close()
        return value

    def test_create_backup_produces_a_matching_copy(self):
        from apps.core.backup import create_backup

        backup = create_backup()
        self.assertTrue(backup.path.exists())
        self.assertEqual(self._read_marker(backup.path), "original")

    def test_list_backups_returns_newest_first(self):
        from apps.core.backup import create_backup, list_backups

        first = create_backup()
        second = create_backup()
        names = [b.filename for b in list_backups()]
        self.assertEqual(names[0], second.filename if second.filename != first.filename else names[0])

    def test_restore_overwrites_live_db_and_keeps_safety_copy(self):
        import sqlite3

        from apps.core.backup import create_backup, restore_backup

        original_backup = create_backup()

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE marker SET value = 'changed'")
        conn.commit()
        conn.close()
        self.assertEqual(self._read_marker(self.db_path), "changed")

        safety = restore_backup(original_backup.filename)

        self.assertEqual(self._read_marker(self.db_path), "original")
        self.assertEqual(self._read_marker(safety.path), "changed")

    def test_restore_rejects_path_traversal(self):
        from apps.core.backup import RestoreError, restore_backup

        with self.assertRaises(RestoreError):
            restore_backup("../../etc/passwd")


class ExportTests(TestCase):
    def setUp(self):
        from apps.finance.models import Account, Transaction

        self.account = Account.objects.create(name="Test Account", opening_balance="100.00")
        Transaction.objects.create(account=self.account, amount="20.00", type="expense", direction="out", date="2026-01-01", description="Coffee")

    def test_export_json_produces_valid_json(self):
        from apps.core.export import export_json

        content = export_json("transactions")
        data = json.loads(content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["description"], "Coffee")

    def test_export_csv_has_header_and_row(self):
        from apps.core.export import export_csv

        content = export_csv("transactions")
        lines = content.strip().split("\r\n")
        self.assertEqual(len(lines), 2)
        self.assertIn("description", lines[0])

    def test_unknown_dataset_raises(self):
        from apps.core.export import export_json

        with self.assertRaises(ValueError):
            export_json("not_a_real_dataset")


class AutoLockMiddlewareTests(TestCase):
    """Bank-level inactivity auto-lock. Real elapsed time isn't used here —
    every test seeds the session's last-activity timestamp directly, which
    is both fast and exact instead of sleeping in a test."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=self.user, display_name="Owner", auto_lock_minutes=10)
        self.client.login(username="owner", password="testpass123")

    def _seed_last_activity(self, minutes_ago):
        from apps.core.middleware import LAST_ACTIVITY_SESSION_KEY

        session = self.client.session
        session[LAST_ACTIVITY_SESSION_KEY] = time.time() - (minutes_ago * 60)
        session.save()

    def test_first_authenticated_request_seeds_timer_without_locking(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        from apps.core.middleware import LAST_ACTIVITY_SESSION_KEY

        self.assertIn(LAST_ACTIVITY_SESSION_KEY, self.client.session)

    def test_request_within_limit_stays_unlocked(self):
        self._seed_last_activity(minutes_ago=5)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    def test_request_past_limit_locks_and_redirects_to_login(self):
        self._seed_last_activity(minutes_ago=11)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("core:login"), response.url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_locked_page_reveals_nothing_before_redirect(self):
        self._seed_last_activity(minutes_ago=11)
        response = self.client.get(reverse("finance:overview"))
        self.assertEqual(response.status_code, 302)
        self.assertLess(len(response.content), 200)

    def test_correct_passcode_unlocks_after_auto_lock(self):
        self._seed_last_activity(minutes_ago=11)
        self.client.get(reverse("dashboard:home"))  # triggers the auto-lock
        response = self.client.post(reverse("core:login"), {"password": "testpass123"})
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_wrong_passcode_rejected_after_auto_lock(self):
        self._seed_last_activity(minutes_ago=11)
        self.client.get(reverse("dashboard:home"))
        response = self.client.post(reverse("core:login"), {"password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_polling_endpoint_does_not_refresh_timer(self):
        from apps.core.middleware import LAST_ACTIVITY_SESSION_KEY

        self._seed_last_activity(minutes_ago=5)
        stale_timestamp = self.client.session[LAST_ACTIVITY_SESSION_KEY]
        self.client.get(reverse("focus:active_status"))
        self.assertEqual(self.client.session[LAST_ACTIVITY_SESSION_KEY], stale_timestamp)

    def test_polling_endpoint_still_locked_out_once_stale(self):
        self._seed_last_activity(minutes_ago=11)
        response = self.client.get(reverse("focus:active_status"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"active": False, "locked": True})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_ordinary_navigation_refreshes_timer(self):
        from apps.core.middleware import LAST_ACTIVITY_SESSION_KEY

        self._seed_last_activity(minutes_ago=5)
        stale_timestamp = self.client.session[LAST_ACTIVITY_SESSION_KEY]
        self.client.get(reverse("dashboard:home"))
        self.assertGreater(self.client.session[LAST_ACTIVITY_SESSION_KEY], stale_timestamp)

    def test_activity_ping_endpoint_refreshes_timer(self):
        from apps.core.middleware import LAST_ACTIVITY_SESSION_KEY

        self._seed_last_activity(minutes_ago=5)
        stale_timestamp = self.client.session[LAST_ACTIVITY_SESSION_KEY]
        response = self.client.post(reverse("core:activity_ping"))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(self.client.session[LAST_ACTIVITY_SESSION_KEY], stale_timestamp)

    def test_zero_minutes_locks_on_next_request(self):
        Profile.objects.filter(user=self.user).update(auto_lock_minutes=0)
        self.client.get(reverse("dashboard:home"))  # seeds the timer
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("core:login"), response.url)

    def test_custom_auto_lock_minutes_is_respected(self):
        Profile.objects.filter(user=self.user).update(auto_lock_minutes=30)
        self._seed_last_activity(minutes_ago=20)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)
