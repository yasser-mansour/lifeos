from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.goals.models import Goal
from apps.notes.models import Note
from apps.people.models import Person
from apps.projects.models import Project
from apps.school.models import Course
from apps.tasks.models import Task


class NoteModelTests(TestCase):
    def test_linked_to_returns_first_related_object(self):
        project = Project.objects.create(name="Northstar")
        note = Note.objects.create(title="Idea", project=project)
        self.assertEqual(note.linked_to, project)

    def test_linked_to_none_when_unlinked(self):
        note = Note.objects.create(title="Standalone")
        self.assertIsNone(note.linked_to)


class NoteViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_state(self):
        response = self.client.get(reverse("notes:list"))
        self.assertContains(response, "No notes yet")

    def test_new_note_and_autosave(self):
        response = self.client.get(reverse("notes:new"))
        note = Note.objects.first()
        self.assertRedirects(response, reverse("notes:detail", args=[note.pk]))
        self.client.post(reverse("notes:autosave", args=[note.pk]), {"title": "Groceries", "content": "milk, eggs"})
        note.refresh_from_db()
        self.assertEqual(note.title, "Groceries")

    def test_new_note_from_project_page_links_immediately(self):
        """Regression: note_new used to ignore all query params and always
        create a completely unlinked note, even when opened from a Project/
        Person/Course/Task/Goal page via a "New Note" link."""
        project = Project.objects.create(name="Northstar")
        self.client.get(reverse("notes:new"), {"project": project.pk})
        note = Note.objects.first()
        self.assertEqual(note.project_id, project.pk)

    def test_new_note_from_person_page_links_immediately(self):
        person = Person.objects.create(name="Sara Bennani")
        self.client.get(reverse("notes:new"), {"person": person.pk})
        note = Note.objects.first()
        self.assertEqual(note.person_id, person.pk)

    def test_new_note_from_course_page_links_immediately(self):
        course = Course.objects.create(name="Algorithms")
        self.client.get(reverse("notes:new"), {"course": course.pk})
        note = Note.objects.first()
        self.assertEqual(note.course_id, course.pk)

    def test_new_note_from_task_page_links_immediately(self):
        task = Task.objects.create(title="Ship it")
        self.client.get(reverse("notes:new"), {"task": task.pk})
        note = Note.objects.first()
        self.assertEqual(note.task_id, task.pk)

    def test_new_note_from_goal_page_links_immediately(self):
        goal = Goal.objects.create(title="Study 100 hours")
        self.client.get(reverse("notes:new"), {"goal": goal.pk})
        note = Note.objects.first()
        self.assertEqual(note.goal_id, goal.pk)

    def test_detail_page_can_reassign_goal(self):
        """Regression: the edit form always had a `goal` field, but the
        template never rendered it — a note could be linked to a goal at
        creation but never re-linked or unlinked afterward from normal UI."""
        goal = Goal.objects.create(title="Study 100 hours")
        note = Note.objects.create(title="Progress log")
        response = self.client.get(note.get_absolute_url())
        self.assertContains(response, f'<option value="{goal.pk}">')

    def test_autosave_can_set_goal_link(self):
        goal = Goal.objects.create(title="Study 100 hours")
        note = Note.objects.create(title="Progress log")
        self.client.post(reverse("notes:autosave", args=[note.pk]), {"title": "Progress log", "content": "", "goal": str(goal.pk)})
        note.refresh_from_db()
        self.assertEqual(note.goal_id, goal.pk)


class NoteEntryPointTests(TestCase):
    """The other side of each relationship: the parent page must show its
    linked notes and offer a real "New Note" entry point."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_project_notes_tab_shows_linked_note(self):
        project = Project.objects.create(name="Northstar")
        Note.objects.create(title="Kickoff notes", project=project)
        response = self.client.get(reverse("projects:detail", args=[project.pk]), {"tab": "notes"})
        self.assertContains(response, "Kickoff notes")

    def test_person_panel_shows_linked_note(self):
        person = Person.objects.create(name="Sara Bennani")
        Note.objects.create(title="Call recap", person=person)
        response = self.client.get(reverse("people:detail", args=[person.pk]))
        self.assertContains(response, "Call recap")

    def test_course_detail_shows_linked_note(self):
        course = Course.objects.create(name="Algorithms")
        Note.objects.create(title="Lecture 3 recap", course=course)
        response = self.client.get(course.get_absolute_url())
        self.assertContains(response, "Lecture 3 recap")
