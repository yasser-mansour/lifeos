"""Development-only fixture data for visually reviewing the UI. Never runs
automatically — see docs/USER_GUIDE.md. All names below are fictional."""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.calendar_app.models import Event
from apps.core.models import Profile
from apps.devices.models import Device
from apps.finance.models import Account, Allocation, Category, Transaction
from apps.finance.services import create_transfer, equal_allocation_plan
from apps.goals.models import Goal
from apps.journal.models import JournalEntry
from apps.people.models import Person
from apps.projects.models import Project
from apps.school.models import Course, Exam, Topic
from apps.study.models import StudySession, StudySessionEvent
from apps.tasks.models import Task
from apps.writing.models import Book, Chapter


class Command(BaseCommand):
    help = "Populate LIFEOS with clearly fictional demo data for UI review. Development only."

    def handle(self, *args, **options):
        if not Profile.objects.exists():
            self.stdout.write(self.style.ERROR("Run first-run setup before seeding demo data."))
            return

        self.stdout.write("Seeding demo data…")
        random.seed(42)

        courses = self._seed_school()
        self._seed_study(courses)
        people = self._seed_people()
        projects = self._seed_projects(people)
        self._seed_tasks(projects, courses, people)
        self._seed_finance(projects, people)
        self._seed_calendar(courses, projects)
        self._seed_journal()
        self._seed_writing()
        self._seed_goals(courses)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    def _seed_school(self):
        specs = [
            ("Mathematics", "Prof. Idrissi", "#4954E0", ["Calculus", "Linear Algebra", "Probability"]),
            ("Physics", "Prof. Bennis", "#17875A", ["Thermodynamics", "Mechanics"]),
            ("Algorithms & Data Structures", "Prof. Chraibi", "#A3660F", ["Graphs", "Dynamic Programming", "Sorting"]),
        ]
        courses = {}
        for name, teacher, color, topics in specs:
            course, _ = Course.objects.get_or_create(name=name, defaults={"teacher": teacher, "color": color})
            courses[name] = course
            for t in topics:
                Topic.objects.get_or_create(course=course, name=t)
        Exam.objects.get_or_create(
            course=courses["Mathematics"], date=timezone.localdate() + timedelta(days=9),
            defaults={"time": "09:00", "location": "Amphi B", "description": "Midterm", "importance": "high"},
        )
        return courses

    def _seed_study(self, courses):
        if StudySession.objects.exists():
            return  # already seeded — StudySession rows aren't get_or_create-safe below
        mac, _ = Device.objects.get_or_create(platform="macos", device_type="primary", defaults={"name": "This Mac", "status": "online"})
        phone, _ = Device.objects.get_or_create(platform="android", device_type="mobile", defaults={"name": "Galaxy A25", "status": "online"})
        course_list = list(courses.values())
        topics_by_course = {c: list(c.topics.all()) for c in course_list}

        today = timezone.localdate()
        for offset in range(30):
            day = today - timedelta(days=offset)
            if offset % 7 in (5,) and offset > 2:  # skip one weekday to make a realistic (non-perfect) streak
                continue
            sessions_today = random.randint(1, 2)
            for _ in range(sessions_today):
                course = random.choice(course_list)
                topic = random.choice(topics_by_course[course]) if topics_by_course[course] else None
                duration_minutes = random.choice([25, 45, 50, 75, 90, 120])
                device = random.choice([mac, phone])
                mode = random.choice(["stopwatch", "countdown", "pomodoro"])
                start_hour = random.choice([8, 9, 14, 16, 20, 21])
                started_at = timezone.make_aware(
                    timezone.datetime.combine(day, timezone.datetime.min.time()) + timedelta(hours=start_hour, minutes=random.randint(0, 59))
                )
                ended_at = started_at + timedelta(minutes=duration_minutes)
                session = StudySession.objects.create(
                    course=course, topic=topic, mode=mode, status="completed",
                    started_at=started_at, ended_at=ended_at, origin_device=device, ending_device=device,
                )
                StudySessionEvent.objects.create(session=session, event_type="start", timestamp=started_at, device=device)
                StudySessionEvent.objects.create(session=session, event_type="finish", timestamp=ended_at, device=device)

    def _seed_people(self):
        specs = [
            ("Yassine Alaoui", "Acme Digital", ["client"], "yassine@acmedigital.ma"),
            ("Sara Bennani", "Northstar", ["client"], "sara@northstar.ma"),
            ("Karim Fassi", "", ["friend"], ""),
            ("Prof. Idrissi", "Northgate University", ["teacher"], ""),
        ]
        people = {}
        for name, org, rel, email in specs:
            person, _ = Person.objects.get_or_create(name=name, defaults={"organization": org, "relationship_types": rel, "email": email})
            people[name] = person
        return people

    def _seed_projects(self, people):
        specs = [
            ("Northstar", "business", "active", "Client SMS/notification platform.", ["Sara Bennani"]),
            ("Atlas Tracker", "business", "active", "Student tracking SaaS for private schools.", ["Yassine Alaoui"]),
            ("Harbor Supply", "business", "paused", "Inventory app for a friend's small shop.", []),
            ("Moving Apartment", "personal", "active", "Move to the new place by end of semester.", []),
        ]
        projects = {}
        for name, area, status, desc, linked_people in specs:
            project, _ = Project.objects.get_or_create(name=name, defaults={"area": area, "status": status, "description": desc, "priority": "high" if area == "business" else "normal"})
            for pname in linked_people:
                project.people.add(people[pname])
            projects[name] = project
        return projects

    def _seed_tasks(self, projects, courses, people):
        today = timezone.localdate()
        specs = [
            ("Finish calculus exercises", "todo", "high", None, courses["Mathematics"], None, today),
            ("Send invoice", "todo", "normal", projects["Atlas Tracker"], None, people["Yassine Alaoui"], today),
            ("Fix SMS callback bug", "in_progress", "urgent", projects["Northstar"], None, None, today + timedelta(days=1)),
            ("Review pull request", "todo", "normal", projects["Northstar"], None, None, None),
            ("Buy moving boxes", "todo", "low", projects["Moving Apartment"], None, None, today + timedelta(days=3)),
            ("Prepare thermodynamics summary", "todo", "normal", None, courses["Physics"], None, today + timedelta(days=2)),
            ("Confirm scope with client", "waiting", "normal", projects["Northstar"], None, people["Sara Bennani"], None),
        ]
        for title, status, priority, project, course, person, due in specs:
            task, created = Task.objects.get_or_create(title=title, defaults={
                "status": status, "priority": priority, "project": project, "course": course, "person": person, "due_date": due,
            })
            if created and status == "waiting":
                task.waiting_on = "Sara"
                task.follow_up_date = today - timedelta(days=1)
                task.save(update_fields=["waiting_on", "follow_up_date"])
        Task.objects.get_or_create(title="Archived idea: rewrite onboarding", defaults={"status": "done", "completed_at": timezone.now() - timedelta(days=2)})

    def _seed_finance(self, projects, people):
        housing, _ = Category.objects.get_or_create(name="Housing")
        food, _ = Category.objects.get_or_create(name="Food")
        transport, _ = Category.objects.get_or_create(name="Transport")
        software, _ = Category.objects.get_or_create(name="Software")

        personal_bank, _ = Account.objects.get_or_create(name="CIH Personal", defaults={"context": "personal", "account_type": "bank", "institution": "CIH Bank", "opening_balance": Decimal("17500.00")})
        cash, _ = Account.objects.get_or_create(name="Cash", defaults={"context": "personal", "account_type": "cash", "opening_balance": Decimal("400.00")})
        business_bank, _ = Account.objects.get_or_create(name="CIH Business", defaults={"context": "business", "account_type": "bank", "institution": "CIH Bank", "opening_balance": Decimal("9000.00")})

        if Transaction.objects.filter(account=personal_bank).exists():
            return  # already seeded

        today = timezone.localdate()
        Transaction.objects.create(account=personal_bank, amount=Decimal("85.00"), type="expense", direction="out", date=today - timedelta(days=1), category=food, description="Groceries")
        Transaction.objects.create(account=personal_bank, amount=Decimal("40.00"), type="expense", direction="out", date=today - timedelta(days=2), category=transport, description="Gas")
        Transaction.objects.create(account=business_bank, amount=Decimal("18000.00"), type="income", direction="in", date=today - timedelta(days=5), person=people["Yassine Alaoui"], project=projects["Atlas Tracker"], description="Atlas Tracker milestone payment")
        Transaction.objects.create(account=business_bank, amount=Decimal("350.00"), type="expense", direction="out", date=today - timedelta(days=4), category=software, project=projects["Northstar"], description="Hosting")

        advance = Transaction.objects.create(account=personal_bank, amount=Decimal("12000.00"), type="expense", direction="out", date=today - timedelta(days=10), category=housing, description="4 months rent, paid in advance")
        for slice_ in equal_allocation_plan(Decimal("12000.00"), today.replace(day=1), 4):
            Allocation.objects.create(transaction=advance, category=housing, **slice_)

        create_transfer(from_account=business_bank, to_account=personal_bank, amount=Decimal("3000.00"), currency="MAD", date=today - timedelta(days=6), description="Owner draw")
        create_transfer(from_account=personal_bank, to_account=cash, amount=Decimal("500.00"), currency="MAD", date=today - timedelta(days=3), description="ATM withdrawal")

    def _seed_calendar(self, courses, projects):
        now = timezone.now()
        Event.objects.get_or_create(title="Northstar client call", defaults={"start": now.replace(hour=15, minute=0, second=0, microsecond=0), "category": "work", "project": projects["Northstar"]})
        Event.objects.get_or_create(title="Physics lecture", defaults={"start": now.replace(hour=9, minute=0, second=0, microsecond=0), "category": "study", "course": courses["Physics"]})

    def _seed_journal(self):
        today = timezone.localdate()
        JournalEntry.objects.get_or_create(date=today, defaults={"title": "Long day", "mood": "good", "body": "Shipped the Northstar callback fix, finally. Study session in the evening felt good — calculus is clicking."})
        JournalEntry.objects.get_or_create(date=today - timedelta(days=2), defaults={"title": "", "mood": "okay", "body": "Slow start but got through the reading."})

    def _seed_writing(self):
        book, _ = Book.objects.get_or_create(title="Notes on Building Things", defaults={"status": "drafting", "description": "Loose essays on building software as a student."})
        Chapter.objects.get_or_create(book=book, order=0, defaults={"title": "Starting Before You're Ready", "content": "Most of what I've built started before I felt ready to build it. " * 8, "status": "draft"})
        Chapter.objects.get_or_create(book=book, order=1, defaults={"title": "On Small Clients", "content": "Working with small clients teaches you constraints fast.", "status": "draft"})

    def _seed_goals(self, courses):
        Goal.objects.get_or_create(title="Study 100 hours this semester", defaults={"goal_type": "academic", "target_value": Decimal("100"), "unit": "hours", "derive_from_study_hours": True})
        Goal.objects.get_or_create(title="Save 5,000 MAD", defaults={"goal_type": "financial", "target_value": Decimal("5000"), "current_value": Decimal("1800"), "unit": "MAD"})
