from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Profile
from apps.school.models import Course, Exam, Topic

# A fixed calendar date eventually becomes "the past" simply because real
# time passes — these tests need an exam that's genuinely upcoming, not a
# specific date, so this is always "soon" no matter when the suite runs
# (found as an unrelated, pre-existing failure while testing Finance V2:
# the hardcoded "2026-09-01" had quietly become 4 days in the past).
UPCOMING_EXAM_DATE = timezone.localdate() + timezone.timedelta(days=7)


class CourseModelTests(TestCase):
    def test_str_and_absolute_url(self):
        course = Course.objects.create(name="Mathematics")
        self.assertEqual(str(course), "Mathematics")
        self.assertIn(str(course.pk), course.get_absolute_url())

    def test_topic_ordering(self):
        course = Course.objects.create(name="Physics")
        Topic.objects.create(course=course, name="Thermo", order=2)
        Topic.objects.create(course=course, name="Mechanics", order=1)
        self.assertEqual(list(course.topics.values_list("name", flat=True)), ["Mechanics", "Thermo"])


class SchoolViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_course_list_empty_state(self):
        response = self.client.get(reverse("school:course_list"))
        self.assertContains(response, "No courses yet")

    def test_create_course(self):
        response = self.client.post(reverse("school:course_create"), {"name": "Calculus II", "color": "#4954E0"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(name="Calculus II").exists())

    def test_course_detail_renders_with_no_sessions(self):
        course = Course.objects.create(name="Algorithms")
        response = self.client.get(course.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algorithms")

    def test_exam_importance_badge(self):
        course = Course.objects.create(name="Chemistry")
        Exam.objects.create(course=course, date=UPCOMING_EXAM_DATE, importance="high", description="Midterm")
        response = self.client.get(course.get_absolute_url())
        self.assertContains(response, "Midterm")

    def test_create_topic_with_only_name_matches_real_modal_submission(self):
        """Regression: the "Add Topic" modal only ever asks for a name — it
        has never rendered an `order` field. TopicForm.order was required
        (the model lacked blank=True despite having default=0), so every
        real submission from that modal silently failed server-side
        validation and redirected back with no topic created and no error
        shown. Caught via live browser testing, not by a unit test — every
        prior test happened to pass `order` explicitly, masking the bug."""
        course = Course.objects.create(name="Linear Algebra")
        response = self.client.post(reverse("school:topic_create", args=[course.pk]), {"name": "Eigenvalues"})
        self.assertRedirects(response, course.get_absolute_url())
        topic = Topic.objects.get(name="Eigenvalues")
        self.assertEqual(topic.course_id, course.pk)
        self.assertEqual(topic.order, 0)

    def test_course_detail_renders_with_topic_and_exam_present(self):
        """Smoke test for the per-row Edit/Delete modal markup — the empty
        states don't exercise that template code path at all."""
        course = Course.objects.create(name="Biology")
        Topic.objects.create(course=course, name="Cells", order=1)
        Exam.objects.create(course=course, date=UPCOMING_EXAM_DATE, importance="medium", description="Final")
        response = self.client.get(course.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cells")
        self.assertContains(response, "Final")

    def test_update_course(self):
        course = Course.objects.create(name="Old Name", teacher="Mx. Old")
        response = self.client.post(reverse("school:course_update", args=[course.pk]), {
            "name": "New Name", "teacher": "Mx. New", "color": "#4954E0", "description": "",
        })
        self.assertRedirects(response, course.get_absolute_url())
        course.refresh_from_db()
        self.assertEqual(course.name, "New Name")
        self.assertEqual(course.teacher, "Mx. New")

    def test_update_topic(self):
        course = Course.objects.create(name="Physics")
        topic = Topic.objects.create(course=course, name="Old Topic", order=1)
        response = self.client.post(reverse("school:topic_update", args=[course.pk, topic.pk]), {"name": "New Topic", "order": 2})
        self.assertRedirects(response, course.get_absolute_url())
        topic.refresh_from_db()
        self.assertEqual(topic.name, "New Topic")
        self.assertEqual(topic.order, 2)

    def test_delete_topic_soft_deletes(self):
        course = Course.objects.create(name="Physics")
        topic = Topic.objects.create(course=course, name="Gone Soon")
        response = self.client.post(reverse("school:topic_delete", args=[course.pk, topic.pk]))
        self.assertRedirects(response, course.get_absolute_url())
        self.assertFalse(Topic.objects.filter(pk=topic.pk).exists())
        self.assertTrue(Topic.all_objects.filter(pk=topic.pk).exists())  # soft delete, not gone

    def test_add_exam_from_course_detail_link_reaches_create_view(self):
        """Regression: exam_create existed but had no UI entry point at all."""
        course = Course.objects.create(name="History")
        response = self.client.post(reverse("school:exam_create"), {
            "course": course.pk, "date": "2026-10-01", "importance": "high", "description": "Oral exam",
        })
        self.assertRedirects(response, course.get_absolute_url())
        self.assertTrue(Exam.objects.filter(description="Oral exam").exists())

    def test_update_exam_can_reassign_course(self):
        course_a = Course.objects.create(name="Course A")
        course_b = Course.objects.create(name="Course B")
        exam = Exam.objects.create(course=course_a, date=UPCOMING_EXAM_DATE, importance="low")
        response = self.client.post(reverse("school:exam_update", args=[exam.pk]), {
            "course": course_b.pk, "date": "2026-09-05", "importance": "high", "description": "Moved",
        })
        self.assertRedirects(response, course_b.get_absolute_url())
        exam.refresh_from_db()
        self.assertEqual(exam.course_id, course_b.pk)
        self.assertEqual(exam.description, "Moved")

    def test_delete_exam_soft_deletes(self):
        course = Course.objects.create(name="Geography")
        exam = Exam.objects.create(course=course, date=UPCOMING_EXAM_DATE, importance="low")
        response = self.client.post(reverse("school:exam_delete", args=[exam.pk]))
        self.assertRedirects(response, course.get_absolute_url())
        self.assertFalse(Exam.objects.filter(pk=exam.pk).exists())
        self.assertTrue(Exam.all_objects.filter(pk=exam.pk).exists())
