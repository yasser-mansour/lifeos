from django import forms

from apps.calendar_app.models import Event
from apps.core.base_forms import StyledModelForm


class EventForm(StyledModelForm):
    class Meta:
        model = Event
        fields = ["title", "start", "end", "all_day", "location", "category", "project", "person", "course", "description"]
        widgets = {
            "start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
