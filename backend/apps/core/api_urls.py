from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.calendar_app.api import EventViewSet
from apps.devices.api import DeviceViewSet, claim_device
from apps.finance.api import AccountViewSet, BudgetViewSet, CategoryViewSet, FundViewSet, RecurringCommitmentViewSet, TransactionViewSet, TransferViewSet
from apps.goals.api import GoalViewSet
from apps.inbox.api import InboxItemViewSet
from apps.journal.api import JournalEntryViewSet
from apps.notes.api import NoteViewSet
from apps.writing.api import BookViewSet, ChapterViewSet
from apps.people.api import OrganizationViewSet, PersonViewSet
from apps.projects.api import ProjectViewSet
from apps.school.api import CourseViewSet, ExamViewSet, TopicViewSet
from apps.study.api import StudyGoalViewSet, StudySessionViewSet
from apps.tasks.api import TaskViewSet

router = DefaultRouter()
router.register("people", PersonViewSet, basename="person")
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("courses", CourseViewSet, basename="course")
router.register("topics", TopicViewSet, basename="topic")
router.register("exams", ExamViewSet, basename="exam")
router.register("projects", ProjectViewSet, basename="project")
router.register("tasks", TaskViewSet, basename="task")
router.register("accounts", AccountViewSet, basename="account")
router.register("funds", FundViewSet, basename="fund")
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("transfers", TransferViewSet, basename="transfer")
router.register("recurring-commitments", RecurringCommitmentViewSet, basename="recurringcommitment")
router.register("budgets", BudgetViewSet, basename="budget")
router.register("categories", CategoryViewSet, basename="category")
router.register("study-sessions", StudySessionViewSet, basename="studysession")
router.register("study-goals", StudyGoalViewSet, basename="studygoal")
router.register("events", EventViewSet, basename="event")
router.register("journal-entries", JournalEntryViewSet, basename="journalentry")
router.register("books", BookViewSet, basename="book")
router.register("chapters", ChapterViewSet, basename="chapter")
router.register("goals", GoalViewSet, basename="goal")
router.register("notes", NoteViewSet, basename="note")
router.register("inbox-items", InboxItemViewSet, basename="inboxitem")
router.register("devices", DeviceViewSet, basename="device")

# The literal /devices/claim/ path must be resolved before the router's
# /devices/<pk>/ pattern, which would otherwise treat "claim" as a pk and
# route into DeviceViewSet (returning 401/405 instead of ever reaching
# claim_device — this exact ordering bug shipped once already).
urlpatterns = [
    path("devices/claim/", claim_device, name="device-claim"),
] + router.urls
