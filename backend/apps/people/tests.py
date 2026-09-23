from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Profile
from apps.people.models import Organization, Person
from apps.projects.models import Project

TODAY = timezone.localdate()


class PersonModelTests(TestCase):
    def test_relationship_labels_map_codes_to_readable_text(self):
        person = Person.objects.create(name="Sara Client", relationship_types=["client", "friend"])
        self.assertEqual(person.relationship_labels, ["Client", "Friend"])
        self.assertTrue(person.is_client)

    def test_soft_delete_hides_from_default_manager(self):
        person = Person.objects.create(name="Temp Contact")
        person.soft_delete()
        self.assertFalse(Person.objects.filter(pk=person.pk).exists())
        self.assertTrue(Person.all_objects.filter(pk=person.pk).exists())

    def test_version_increments_on_update(self):
        person = Person.objects.create(name="Versioned")
        self.assertEqual(person.version, 1)
        person.phone = "0600000000"
        person.save()
        person.refresh_from_db()
        self.assertEqual(person.version, 2)


class PersonViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner", default_currency="MAD")
        self.client.login(username="owner", password="testpass123")

    def test_list_view_renders(self):
        Person.objects.create(name="Ada Lovelace")
        response = self.client.get(reverse("people:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")

    def test_create_person_via_form(self):
        response = self.client.post(reverse("people:create"), {"name": "New Client", "relationship_types": ["client"]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Person.objects.filter(name="New Client").exists())

    def test_empty_state_when_no_people(self):
        # Copy updated for the combined People & Organizations list (spec
        # §2) — "No people yet" would be inaccurate wording for a list that
        # can also be empty of organizations.
        response = self.client.get(reverse("people:list"))
        self.assertContains(response, "Nothing here yet")

    def test_detail_page_renders_with_linked_project_and_client_finance(self):
        """Smoke test for the detail panel's Projects/Finance/Edit blocks —
        the create/list tests never exercise this template at all. Finance
        V2 (spec §6) made this section unconditional and renamed its
        figures Received/Sent/Net rather than Total revenue/Total paid out,
        so this asserts the new copy."""
        person = Person.objects.create(name="Sara Client", relationship_types=["client"])
        project = Project.objects.create(name="Northstar")
        project.people.add(person)
        response = self.client.get(reverse("people:detail", args=[person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Northstar")
        self.assertContains(response, "No financial activity yet")


class PersonUpdateTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_update_changes_fields(self):
        person = Person.objects.create(name="Old Name")
        response = self.client.post(reverse("people:update", args=[person.pk]), {
            "name": "New Name", "email": "new@example.com", "phone": "", "organization": "", "notes": "", "relationship_types": [],
        })
        self.assertEqual(response.status_code, 200)
        person.refresh_from_db()
        self.assertEqual(person.name, "New Name")
        self.assertEqual(person.email, "new@example.com")


class PersonProjectLinkTests(TestCase):
    """Reverse-direction of the Project↔Person link — Project side already
    had link/unlink; these confirm Person side has full parity."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_link_project_from_person_page(self):
        person = Person.objects.create(name="Sara Bennani")
        project = Project.objects.create(name="Northstar")
        response = self.client.post(reverse("people:link_project", args=[person.pk]), {"project_id": str(project.pk)})
        self.assertRedirects(response, reverse("people:detail", args=[person.pk]))
        self.assertIn(project, person.projects.all())

    def test_unlink_project_from_person_page(self):
        person = Person.objects.create(name="Sara Bennani")
        project = Project.objects.create(name="Northstar")
        project.people.add(person)
        response = self.client.post(reverse("people:unlink_project", args=[person.pk, project.pk]))
        self.assertRedirects(response, reverse("people:detail", args=[person.pk]))
        self.assertNotIn(project, person.projects.all())
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())  # unlink, not delete

    def test_available_projects_excludes_already_linked(self):
        person = Person.objects.create(name="Sara Bennani")
        linked = Project.objects.create(name="Northstar")
        unlinked = Project.objects.create(name="Atlas Tracker")
        project = linked
        project.people.add(person)
        response = self.client.get(reverse("people:detail", args=[person.pk]))
        self.assertNotContains(response, f'<option value="{linked.pk}">')
        self.assertContains(response, "Atlas Tracker")


class OrganizationModelTests(TestCase):
    def test_relationship_labels_and_is_client_shared_with_person(self):
        org = Organization.objects.create(name="Heroku", relationship_types=["service_provider"])
        self.assertEqual(org.relationship_labels, ["Service Provider"])
        self.assertFalse(org.is_client)
        school = Organization.objects.create(name="School ABC", relationship_types=["client", "school"])
        self.assertTrue(school.is_client)

    def test_soft_delete_hides_from_default_manager_but_keeps_the_row(self):
        org = Organization.objects.create(name="Temp Org")
        org.soft_delete()
        self.assertFalse(Organization.objects.filter(pk=org.pk).exists())
        self.assertTrue(Organization.all_objects.filter(pk=org.pk).exists())

    def test_archived_is_independent_of_soft_delete(self):
        """Two different tiers (spec §46/§82): `archived` is the low-drama
        toggle, deleted_at (soft_delete) is the deliberate one — neither
        implies the other."""
        org = Organization.objects.create(name="Old Client")
        org.archived = True
        org.save(update_fields=["archived"])
        self.assertTrue(Organization.objects.filter(pk=org.pk).exists())  # still not soft-deleted
        self.assertTrue(Organization.objects.get(pk=org.pk).archived)


class OrganizationViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner", default_currency="MAD")
        self.client.login(username="owner", password="testpass123")

    def test_create_organization_via_form(self):
        response = self.client.post(reverse("people:org_create"), {"name": "Heroku", "category": "hosting", "relationship_types": ["service_provider"]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Organization.objects.filter(name="Heroku").exists())

    def test_detail_page_renders_with_financial_summary(self):
        org = Organization.objects.create(name="Heroku", relationship_types=["service_provider"])
        account = self._business_account()
        from apps.finance.models import Transaction

        Transaction.objects.create(account=account, amount=Decimal("120"), type="expense", direction="out", date=TODAY, organization=org)
        response = self.client.get(reverse("people:org_detail", args=[org.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Heroku")
        self.assertContains(response, "1 transaction")

    def test_archive_toggle_does_not_delete(self):
        org = Organization.objects.create(name="Heroku")
        self.client.post(reverse("people:org_archive_toggle", args=[org.pk]))
        org.refresh_from_db()
        self.assertTrue(org.archived)
        self.assertTrue(Organization.objects.filter(pk=org.pk).exists())

    def test_delete_soft_deletes_and_preserves_transactions(self):
        from apps.finance.models import Transaction

        org = Organization.objects.create(name="Heroku")
        account = self._business_account()
        txn = Transaction.objects.create(account=account, amount=Decimal("50"), type="expense", direction="out", date=TODAY, organization=org)
        self.client.post(reverse("people:org_delete", args=[org.pk]))
        self.assertFalse(Organization.objects.filter(pk=org.pk).exists())
        txn.refresh_from_db()
        self.assertEqual(txn.organization_id, org.pk)  # history untouched

    def test_link_and_unlink_project(self):
        org = Organization.objects.create(name="Heroku")
        project = Project.objects.create(name="Northstar")
        self.client.post(reverse("people:org_link_project", args=[org.pk]), {"project_id": str(project.pk)})
        self.assertIn(project, org.projects.all())
        self.client.post(reverse("people:org_unlink_project", args=[org.pk, project.pk]))
        self.assertNotIn(project, org.projects.all())

    def _business_account(self):
        from apps.finance.models import Account

        return Account.objects.create(name="Business Bank", context="business", opening_balance=Decimal("0"))


class CombinedPeopleAndOrganizationsListTests(TestCase):
    """Spec §2/§11 — one list, filterable by type and relationship."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        Person.objects.create(name="Sara Bennani", relationship_types=["family"])
        Organization.objects.create(name="Heroku", relationship_types=["service_provider"])
        Organization.objects.create(name="School ABC", relationship_types=["client"])

    def test_unfiltered_list_shows_both_kinds(self):
        response = self.client.get(reverse("people:list"))
        self.assertContains(response, "Sara Bennani")
        self.assertContains(response, "Heroku")
        self.assertContains(response, "School ABC")

    def test_type_filter_person_excludes_organizations(self):
        response = self.client.get(reverse("people:list"), {"type": "person"})
        self.assertContains(response, "Sara Bennani")
        self.assertNotContains(response, "Heroku")

    def test_type_filter_organization_excludes_people(self):
        response = self.client.get(reverse("people:list"), {"type": "organization"})
        self.assertContains(response, "Heroku")
        self.assertContains(response, "School ABC")
        self.assertNotContains(response, "Sara Bennani")

    def test_relationship_filter_applies_to_both_kinds(self):
        response = self.client.get(reverse("people:list"), {"relationship": "client"})
        self.assertContains(response, "School ABC")
        self.assertNotContains(response, "Heroku")
        self.assertNotContains(response, "Sara Bennani")

    def test_archived_organization_excluded_from_list(self):
        archived = Organization.objects.get(name="Heroku")
        archived.archived = True
        archived.save(update_fields=["archived"])
        response = self.client.get(reverse("people:list"))
        self.assertNotContains(response, "Heroku")


class PersonFinancialSummaryOnDetailTests(TestCase):
    """Spec §6 — EVERY person shows financial interactions, not only
    relationship_types containing "client"."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_non_client_person_still_shows_financial_summary(self):
        from apps.finance.models import Account, Transaction

        father = Person.objects.create(name="Father", relationship_types=["family"])
        account = Account.objects.create(name="Personal Bank", context="personal", opening_balance=Decimal("0"))
        Transaction.objects.create(account=account, amount=Decimal("3000"), type="income", direction="in", date=TODAY, person=father)
        response = self.client.get(reverse("people:detail", args=[father.pk]))
        self.assertContains(response, "Financial activity")
        self.assertContains(response, "3,000.00")

    def test_person_with_no_transactions_shows_empty_state_not_a_crash(self):
        person = Person.objects.create(name="No Money Yet")
        response = self.client.get(reverse("people:detail", args=[person.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No financial activity yet")


class OrganizationApiTests(TestCase):
    """Android parity (spec §86/§88) — Organization needs to actually be
    reachable through the sync API, not just the desktop templates."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_create_organization_via_api(self):
        response = self.client.post("/api/organizations/", {"name": "Heroku", "category": "hosting"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Organization.objects.filter(name="Heroku").exists())

    def test_deleted_organization_is_flagged_on_incremental_pull(self):
        org = Organization.objects.create(name="Old Vendor")
        cutoff = (timezone.now() - timezone.timedelta(minutes=5)).isoformat()
        org.soft_delete()
        response = self.client.get("/api/organizations/", {"modified_since": cutoff})
        rows = {row["id"]: row for row in response.json()["results"]}
        self.assertTrue(rows[str(org.pk)]["deleted"])
