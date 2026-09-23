from django import forms

from apps.core.base_forms import StyledModelForm
from apps.projects.models import Project


class ProjectForm(StyledModelForm):
    # `people` is deliberately excluded: it's a ModelForm M2M field, and if it
    # were included but left unrendered (as in the edit form, where linking
    # people has its own dedicated tab with real link/unlink semantics —
    # see projects/detail.html "People" tab), Django would still clean it as
    # an empty selection on every save and silently unlink everyone.
    class Meta:
        model = Project
        fields = ["name", "area", "status", "priority", "start_date", "target_date", "description"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "target_date": forms.DateInput(attrs={"type": "date"}),
        }
