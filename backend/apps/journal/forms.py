from django import forms

from apps.core.base_forms import StyledModelForm
from apps.journal.models import JournalEntry


class JournalEntryForm(StyledModelForm):
    class Meta:
        model = JournalEntry
        fields = ["date", "title", "mood", "body", "project", "goal"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "body": forms.Textarea(attrs={"rows": 16})}
