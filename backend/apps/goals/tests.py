from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.goals.models import Goal
from apps.projects.models import Project
from apps.school.models import Course


class GoalModelTests(TestCase):
    def test_progress_percent_computed_from_target(self):
        goal = Goal.objects.create(title="Save for laptop", target_value=Decimal("5000"), current_value=Decimal("2500"))
        self.assertEqual(goal.progress_percent, 50)

    def test_progress_percent_none_without_target(self):
        goal = Goal.objects.create(title="Read more")
        self.assertIsNone(goal.progress_percent)

    def test_progress_clamped_at_100(self):
        goal = Goal.objects.create(title="Overshot", target_value=Decimal("100"), current_value=Decimal("150"))
        self.assertEqual(goal.progress_percent, 100)


class GoalViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_state(self):
        response = self.client.get(reverse("goals:list"))
        self.assertContains(response, "No goals yet")

    def test_create_goal(self):
        self.client.post(reverse("goals:create"), {"title": "Study 100 hours", "goal_type": "academic", "target_value": "100", "unit": "hours"})
        self.assertTrue(Goal.objects.filter(title="Study 100 hours").exists())

    def test_update_progress_marks_completed_at_target(self):
        goal = Goal.objects.create(title="Save 1000", target_value=Decimal("1000"))
        self.client.post(reverse("goals:update_progress", args=[goal.pk]), {"current_value": "1000"})
        goal.refresh_from_db()
        self.assertEqual(goal.status, "completed")

    def test_new_goal_from_project_page_prefills_project(self):
        """Regression: GoalForm always had a project/course field, but no
        template ever rendered it — a goal created from a Project page had
        no way to actually end up linked to that project."""
        project = Project.objects.create(name="Northstar")
        response = self.client.get(reverse("goals:list"), {"project": project.pk, "new": "1"})
        self.assertContains(response, f'<option value="{project.pk}" selected>')

    def test_new_goal_from_course_page_prefills_course(self):
        course = Course.objects.create(name="Algorithms")
        response = self.client.get(reverse("goals:list"), {"course": course.pk, "new": "1"})
        self.assertContains(response, f'<option value="{course.pk}" selected>')

    def test_create_goal_with_project_link(self):
        project = Project.objects.create(name="Northstar")
        self.client.post(reverse("goals:create"), {
            "title": "Ship v1", "goal_type": "project", "target_value": "", "unit": "", "project": str(project.pk),
        })
        goal = Goal.objects.get(title="Ship v1")
        self.assertEqual(goal.project_id, project.pk)


class GoalDetailTests(TestCase):
    """Regression coverage: Goal had no detail page at all — no way to
    inspect, edit, or remove a goal (or its Project/Course link) from
    normal UI once created."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_detail_page_renders(self):
        goal = Goal.objects.create(title="Study 100 hours", target_value=Decimal("100"), current_value=Decimal("40"), unit="hours")
        response = self.client.get(goal.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Study 100 hours")

    def test_detail_page_shows_linked_project_and_course(self):
        project = Project.objects.create(name="Northstar")
        course = Course.objects.create(name="Algorithms")
        goal = Goal.objects.create(title="Dual-linked goal", project=project, course=course)
        response = self.client.get(goal.get_absolute_url())
        self.assertContains(response, "Northstar")
        self.assertContains(response, "Algorithms")

    def test_update_goal_changes_fields_and_project_link(self):
        old_project = Project.objects.create(name="Old Project")
        new_project = Project.objects.create(name="New Project")
        goal = Goal.objects.create(title="Old Title", project=old_project)
        response = self.client.post(reverse("goals:update", args=[goal.pk]), {
            "title": "New Title", "goal_type": "personal", "target_value": "", "unit": "", "project": str(new_project.pk), "course": "",
        })
        self.assertRedirects(response, goal.get_absolute_url())
        goal.refresh_from_db()
        self.assertEqual(goal.title, "New Title")
        self.assertEqual(goal.project_id, new_project.pk)

    def test_update_goal_can_remove_project_link(self):
        project = Project.objects.create(name="Northstar")
        goal = Goal.objects.create(title="Linked goal", project=project)
        self.client.post(reverse("goals:update", args=[goal.pk]), {
            "title": goal.title, "goal_type": "personal", "target_value": "", "unit": "", "project": "", "course": "",
        })
        goal.refresh_from_db()
        self.assertIsNone(goal.project)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())  # unlink, not delete

    def test_delete_goal_soft_deletes(self):
        goal = Goal.objects.create(title="Gone Soon")
        response = self.client.post(reverse("goals:delete", args=[goal.pk]))
        self.assertRedirects(response, reverse("goals:list"))
        self.assertFalse(Goal.objects.filter(pk=goal.pk).exists())
        self.assertTrue(Goal.all_objects.filter(pk=goal.pk).exists())


class ProjectAndCourseGoalTabTests(TestCase):
    """The other side of the Project/Course ↔ Goal relationship: the parent
    page must show linked goals and offer a real create-in-context entry
    point, not just the Goal side knowing about its parent."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_project_goals_tab_shows_linked_goal(self):
        project = Project.objects.create(name="Northstar")
        Goal.objects.create(title="Ship v1", project=project)
        response = self.client.get(reverse("projects:detail", args=[project.pk]), {"tab": "goals"})
        self.assertContains(response, "Ship v1")

    def test_course_detail_shows_linked_goal(self):
        course = Course.objects.create(name="Algorithms")
        Goal.objects.create(title="Finish the course with an A", course=course)
        response = self.client.get(course.get_absolute_url())
        self.assertContains(response, "Finish the course with an A")
