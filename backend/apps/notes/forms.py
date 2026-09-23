from django import forms

from apps.core.base_forms import StyledModelForm
from apps.notes.models import Note


class NoteForm(StyledModelForm):
    class Meta:
        model = Note
        fields = ["title", "content", "project", "task", "person", "course", "goal"]
        widgets = {"content": forms.Textarea(attrs={"rows": 12})}
