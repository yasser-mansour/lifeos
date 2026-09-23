from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Profile
from apps.people.models import Person
from apps.projects.models import Project
from apps.school.models import Course
from apps.tasks.models import Task
from apps.tasks.services import next_tasks


class TaskModelTests(TestCase):
    def test_is_overdue_true_for_past_due_open_task(self):
        task = Task.objects.create(title="Late thing", due_date=timezone.localdate() - timedelta(days=1), status="todo")
        self.assertTrue(task.is_overdue)

    def test_is_overdue_false_once_done(self):
        task = Task.objects.create(title="Finished", due_date=timezone.localdate() - timedelta(days=1), status="done")
        self.assertFalse(task.is_overdue)

    def test_mark_done_sets_completed_at(self):
        task = Task.objects.create(title="Do it")
        self.assertIsNone(task.completed_at)
        task.mark_done()
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.completed_at)

    def test_mark_waiting_sets_status_and_follow_up(self):
        task = Task.objects.create(title="Ask about invoice")
        follow_up = timezone.localdate() + timedelta(days=3)
        task.mark_waiting(waiting_on="Client A", follow_up_date=follow_up)
        self.assertEqual(task.status, "waiting")
        self.assertEqual(task.waiting_on, "Client A")
        self.assertEqual(task.follow_up_date, follow_up)

    def test_is_waiting_overdue(self):
        task = Task.objects.create(title="Old ask", status="waiting", follow_up_date=timezone.localdate() - timedelta(days=1))
        self.assertTrue(task.is_waiting_overdue)


class TaskViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_today_view_shows_only_todays_open_tasks(self):
        Task.objects.create(title="Today task", due_date=timezone.localdate(), status="todo")
        Task.objects.create(title="Future task", due_date=timezone.localdate() + timedelta(days=5), status="todo")
        response = self.client.get(reverse("tasks:list"), {"view": "today"})
        self.assertContains(response, "Today task")
        self.assertNotContains(response, "Future task")

    def test_overdue_view(self):
        Task.objects.create(title="Overdue task", due_date=timezone.localdate() - timedelta(days=2), status="todo")
        response = self.client.get(reverse("tasks:list"), {"view": "overdue"})
        self.assertContains(response, "Overdue task")

    def test_all_view_shows_undated_task(self):
        """Regression: a task created with no due date (the New Task modal's
        default when the user doesn't set one) never matched Today/Upcoming/
        Overdue (all require a due_date) and Inbox only ever shows
        status="inbox", which nothing in the UI creates — so an undated task
        was permanently unreachable through any tab. The All tab now covers
        every open task regardless of due date."""
        Task.objects.create(title="Someday task", status="todo")
        response = self.client.get(reverse("tasks:list"), {"view": "all"})
        self.assertContains(response, "Someday task")

    def test_complete_toggle(self):
        task = Task.objects.create(title="Toggle me")
        self.client.post(reverse("tasks:complete", args=[task.pk]), {"next": "/tasks/"})
        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.client.post(reverse("tasks:complete", args=[task.pk]), {"next": "/tasks/"})
        task.refresh_from_db()
        self.assertEqual(task.status, "todo")

    def test_create_task(self):
        response = self.client.post(reverse("tasks:create"), {"title": "New task", "priority": "high"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Task.objects.filter(title="New task").exists())

    def test_new_task_from_project_page_prefills_project(self):
        """Regression: ?project= used to only filter the list; the New Task
        form itself stayed blank, so the task you created didn't actually
        get linked to the project you opened it from unless you noticed and
        manually reselected it in "More options"."""
        project = Project.objects.create(name="Northstar")
        response = self.client.get(reverse("tasks:list"), {"project": project.pk, "new": "1"})
        self.assertContains(response, f'<option value="{project.pk}" selected>')

    def test_new_task_from_course_page_prefills_course(self):
        course = Course.objects.create(name="Algorithms")
        response = self.client.get(reverse("tasks:list"), {"course": course.pk, "new": "1"})
        self.assertContains(response, f'<option value="{course.pk}" selected>')

    def test_new_task_from_person_page_prefills_person(self):
        person = Person.objects.create(name="Sara Bennani")
        response = self.client.get(reverse("tasks:list"), {"person": person.pk, "new": "1"})
        self.assertContains(response, f'<option value="{person.pk}" selected>')

    def test_person_filter_scopes_task_list(self):
        person = Person.objects.create(name="Sara Bennani")
        other = Person.objects.create(name="Yassine Alaoui")
        Task.objects.create(title="For Sara", person=person, due_date=timezone.localdate())
        Task.objects.create(title="For Yassine", person=other, due_date=timezone.localdate())
        response = self.client.get(reverse("tasks:list"), {"person": person.pk, "view": "today"})
        self.assertContains(response, "For Sara")
        self.assertNotContains(response, "For Yassine")


class NextTasksOrderingTests(TestCase):
    """Home's "Next Tasks" ordering (spec §66/§67/§103): overdue tasks
    first, then today-or-later dated tasks, then undated tasks — priority
    is the primary sort within each group, date/created_at only break ties.
    Done/cancelled tasks never appear."""

    def setUp(self):
        today = timezone.localdate()
        self.urgent_overdue = Task.objects.create(title="Urgent overdue", priority="urgent", due_date=today - timedelta(days=2), status="todo")
        self.high_due_tomorrow = Task.objects.create(title="High due tomorrow", priority="high", due_date=today + timedelta(days=1), status="todo")
        self.normal_due_today = Task.objects.create(title="Normal due today", priority="normal", due_date=today, status="todo")
        self.low_due_later = Task.objects.create(title="Low due later", priority="low", due_date=today + timedelta(days=5), status="todo")
        self.urgent_no_due = Task.objects.create(title="Urgent no due date", priority="urgent", status="todo")
        self.normal_no_due = Task.objects.create(title="Normal no due date", priority="normal", status="todo")
        self.completed = Task.objects.create(title="Completed task", priority="urgent", status="done")

    def test_exact_ordering_across_all_three_groups(self):
        result = next_tasks()
        self.assertEqual(
            [t.title for t in result],
            [
                "Urgent overdue",       # Group A: overdue
                "High due tomorrow",    # Group B: dated, priority-sorted (not date-sorted)
                "Normal due today",
                "Low due later",
                "Urgent no due date",   # Group C: undated, priority-sorted
                "Normal no due date",
            ],
        )

    def test_completed_tasks_never_appear(self):
        result = next_tasks()
        self.assertNotIn(self.completed, result)

    def test_limit_returns_top_five(self):
        result = next_tasks(limit=5)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[-1].title, "Urgent no due date")
        self.assertNotIn(self.normal_no_due, result)

    def test_dated_tasks_always_outrank_undated_regardless_of_priority(self):
        """A low-priority task with a due date still isn't more urgent than
        an unscheduled one in absolute terms, but spec §66 is explicit:
        every dated task (group A/B) precedes every undated task (group C)."""
        result = next_tasks()
        self.assertLess(result.index(self.low_due_later), result.index(self.urgent_no_due))

    def test_same_priority_dated_tasks_break_ties_by_due_date_then_created_at(self):
        today = timezone.localdate()
        first = Task.objects.create(title="Earlier due", priority="normal", due_date=today + timedelta(days=1), status="todo")
        second = Task.objects.create(title="Later due, same priority", priority="normal", due_date=today + timedelta(days=3), status="todo")
        result = next_tasks()
        self.assertLess(result.index(first), result.index(second))


class HomeNextTasksViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_home_shows_next_tasks_section(self):
        Task.objects.create(title="Ship the report", priority="high", due_date=timezone.localdate(), status="todo")
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Ship the report")

    def test_home_caps_at_five_and_shows_more_link(self):
        for i in range(7):
            Task.objects.create(title=f"Task {i}", priority="normal", status="todo")
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Task 0")
        self.assertContains(response, "Task 4")
        self.assertNotContains(response, "Task 5")
        self.assertContains(response, "Show more")

    def test_home_empty_state_when_no_open_tasks(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Nothing next")


class WaitingViewRegressionTests(TestCase):
    """Regression: `{{ task.waiting_on|default:task.waiting_for_person.name }}`
    crashed the entire Waiting tab with an unhandled VariableDoesNotExist
    the moment any waiting task had no linked person — which was every
    waiting task, since mark_waiting() and the only UI for it never set
    waiting_for_person at all (see forms.py's WaitingForm vs. what
    _detail_panel.html actually rendered). Django's `default` filter only
    guards its own value, not a dotted-lookup argument that resolves to
    None partway through — that argument resolution isn't wrapped the way
    top-level variable rendering is."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_waiting_view_with_free_text_reason_and_no_person(self):
        Task.objects.create(title="Ask landlord", status="waiting", waiting_on="a reply from the landlord")
        response = self.client.get(reverse("tasks:list"), {"view": "waiting"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Waiting on a reply from the landlord")

    def test_waiting_view_with_linked_person_and_no_free_text(self):
        person = Person.objects.create(name="Sara Bennani")
        Task.objects.create(title="Chase invoice", status="waiting", waiting_for_person=person)
        response = self.client.get(reverse("tasks:list"), {"view": "waiting"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Waiting on Sara Bennani")

    def test_waiting_view_with_both_person_and_free_text(self):
        person = Person.objects.create(name="Sara Bennani")
        Task.objects.create(title="Chase invoice", status="waiting", waiting_for_person=person, waiting_on="signed contract")
        response = self.client.get(reverse("tasks:list"), {"view": "waiting"})
        self.assertContains(response, "Waiting on Sara Bennani — signed contract")

    def test_waiting_view_with_neither_set(self):
        Task.objects.create(title="Vague wait", status="waiting")
        response = self.client.get(reverse("tasks:list"), {"view": "waiting"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vague wait")

    def test_detail_panel_lets_you_pick_a_waiting_person(self):
        """Regression: WaitingForm always had waiting_for_person as a real
        field, but the template only ever rendered waiting_on under a "Who"
        label — the person picker itself was unreachable from any UI."""
        person = Person.objects.create(name="Sara Bennani")
        task = Task.objects.create(title="Chase invoice")
        response = self.client.get(reverse("tasks:detail_panel", args=[task.pk]))
        self.assertContains(response, f'<option value="{person.pk}">Sara Bennani</option>')

    def test_marking_waiting_can_set_the_linked_person(self):
        person = Person.objects.create(name="Sara Bennani")
        task = Task.objects.create(title="Chase invoice")
        self.client.post(reverse("tasks:detail_panel", args=[task.pk]), {
            "waiting_for_person": person.pk, "waiting_on": "", "follow_up_date": "", "notes": "",
        })
        task.refresh_from_db()
        self.assertEqual(task.status, "waiting")
        self.assertEqual(task.waiting_for_person, person)


class TaskUpdateTests(TestCase):
    """Regression coverage for task_update — previously no edit view existed
    for Task at all, so project/course/person could only ever be set once,
    at creation, with no way to change or remove them without the admin."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_update_changes_fields(self):
        task = Task.objects.create(title="Old title", priority="normal")
        response = self.client.post(reverse("tasks:update", args=[task.pk]), {
            "title": "New title", "priority": "high", "due_date": "", "due_time": "", "description": "", "estimated_minutes": "",
        })
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.title, "New title")
        self.assertEqual(task.priority, "high")

    def test_update_can_assign_project(self):
        task = Task.objects.create(title="Needs a home")
        project = Project.objects.create(name="Northstar")
        self.client.post(reverse("tasks:update", args=[task.pk]), {
            "title": task.title, "priority": "normal", "project": str(project.pk), "due_date": "", "due_time": "", "description": "", "estimated_minutes": "",
        })
        task.refresh_from_db()
        self.assertEqual(task.project_id, project.pk)

    def test_update_preserves_tags_when_resubmitted(self):
        """Regression: tags is an M2M field on TaskForm; if the edit form
        didn't render it, resubmitting the edit form would silently clear
        every tag (same class of bug as the Project↔People wipe)."""
        from apps.core.models import Tag

        tag = Tag.objects.create(name="urgent-client-work")
        task = Task.objects.create(title="Tagged task")
        task.tags.add(tag)
        self.client.post(reverse("tasks:update", args=[task.pk]), {
            "title": task.title, "priority": "normal", "due_date": "", "due_time": "", "description": "", "estimated_minutes": "", "tags": [str(tag.pk)],
        })
        task.refresh_from_db()
        self.assertIn(tag, task.tags.all())

    def test_update_can_remove_project_without_deleting_task_or_project(self):
        project = Project.objects.create(name="Northstar")
        task = Task.objects.create(title="Linked task", project=project)
        self.client.post(reverse("tasks:update", args=[task.pk]), {
            "title": task.title, "priority": "normal", "project": "", "due_date": "", "due_time": "", "description": "", "estimated_minutes": "",
        })
        task.refresh_from_db()
        self.assertIsNone(task.project)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())  # unlink, not delete
