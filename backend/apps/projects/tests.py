from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.people.models import Person
from apps.projects.models import Project


class ProjectModelTests(TestCase):
    def test_clients_property_filters_by_relationship(self):
        project = Project.objects.create(name="Northstar", area="business")
        client = Person.objects.create(name="Acme Corp", relationship_types=["client"])
        friend = Person.objects.create(name="A Friend", relationship_types=["friend"])
        project.people.add(client, friend)
        self.assertEqual(project.clients, [client])

    def test_default_status_is_active(self):
        project = Project.objects.create(name="New thing")
        self.assertEqual(project.status, "active")


class ProjectViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_state(self):
        response = self.client.get(reverse("projects:list"))
        self.assertContains(response, "No projects yet")

    def test_create_and_view_project(self):
        response = self.client.post(reverse("projects:create"), {"name": "Atlas Tracker", "area": "business", "status": "active", "priority": "normal"})
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(name="Atlas Tracker")
        detail = self.client.get(project.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Atlas Tracker")

    def test_area_filter(self):
        Project.objects.create(name="Business One", area="business")
        Project.objects.create(name="Personal One", area="personal")
        response = self.client.get(reverse("projects:list"), {"area": "business"})
        self.assertContains(response, "Business One")
        self.assertNotContains(response, "Personal One")

    def test_link_person_to_project(self):
        project = Project.objects.create(name="Northstar")
        person = Person.objects.create(name="Sara Bennani")
        response = self.client.post(reverse("projects:link_person", args=[project.pk]), {"person_id": str(person.pk)})
        self.assertRedirects(response, f"{reverse('projects:detail', args=[project.pk])}?tab=people")
        self.assertIn(person, project.people.all())

    def test_people_tab_shows_linked_person(self):
        project = Project.objects.create(name="Northstar")
        person = Person.objects.create(name="Sara Bennani")
        project.people.add(person)
        response = self.client.get(reverse("projects:detail", args=[project.pk]), {"tab": "people"})
        self.assertContains(response, "Sara Bennani")
        self.assertContains(response, "Unlink")

    def test_unlink_person_from_project(self):
        project = Project.objects.create(name="Northstar")
        person = Person.objects.create(name="Sara Bennani")
        project.people.add(person)
        response = self.client.post(reverse("projects:unlink_person", args=[project.pk, person.pk]))
        self.assertRedirects(response, f"{reverse('projects:detail', args=[project.pk])}?tab=people")
        self.assertNotIn(person, project.people.all())

    def test_editing_a_project_does_not_wipe_linked_people(self):
        """Regression: ProjectForm used to include the M2M `people` field
        without any template ever rendering it (neither create nor edit) —
        Django cleans an unrendered required=False M2M field as empty, so
        every edit save silently called project.people.set([]), unlinking
        everyone. `people` is now excluded from the form entirely; the
        People tab's dedicated link/unlink endpoints own that relationship."""
        project = Project.objects.create(name="Northstar")
        person = Person.objects.create(name="Sara Bennani")
        project.people.add(person)
        response = self.client.post(reverse("projects:update", args=[project.pk]), {
            "name": "Northstar Renamed", "area": "business", "status": "active", "priority": "normal",
        })
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.name, "Northstar Renamed")
        self.assertIn(person, project.people.all())

    def test_available_people_excludes_already_linked(self):
        project = Project.objects.create(name="Northstar")
        linked = Person.objects.create(name="Sara Bennani")
        unlinked = Person.objects.create(name="Yassine Alaoui")
        project.people.add(linked)
        response = self.client.get(reverse("projects:detail", args=[project.pk]), {"tab": "people"})
        self.assertNotContains(response, '<option value="%s">' % linked.pk)
        self.assertContains(response, "Yassine Alaoui")
