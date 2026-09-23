from django import forms

from apps.core.base_forms import StyledModelForm
from apps.goals.models import Goal


class GoalForm(StyledModelForm):
    class Meta:
        model = Goal
        fields = ["title", "goal_type", "target_value", "unit", "deadline", "project", "course", "derive_from_study_hours", "description"]
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}


class GoalProgressForm(StyledModelForm):
    class Meta:
        model = Goal
        fields = ["current_value"]
