from django import forms

from apps.core.base_forms import StyledModelForm
from apps.tasks.models import Task


class TaskForm(StyledModelForm):
    """Status is deliberately not a field here — new tasks always start at
    the model's default ("todo"); status changes happen through dedicated
    actions (Complete, Mark Waiting) rather than this creation form."""

    class Meta:
        model = Task
        fields = ["title", "priority", "due_date", "due_time", "project", "course", "person", "description", "estimated_minutes", "tags"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "due_time": forms.TimeInput(attrs={"type": "time"}),
        }


class WaitingForm(StyledModelForm):
    class Meta:
        model = Task
        fields = ["waiting_on", "waiting_for_person", "follow_up_date", "notes"]
        widgets = {"follow_up_date": forms.DateInput(attrs={"type": "date"})}
