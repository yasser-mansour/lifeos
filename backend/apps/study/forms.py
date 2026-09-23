from django import forms

from apps.core.base_forms import StyledForm
from apps.school.models import Course, Topic
from apps.study.models import DOMAIN_CHOICES
from apps.tasks.models import Task
from apps.projects.models import Project
from apps.writing.models import Book

COUNTDOWN_PRESETS = [10, 15, 25, 30, 45, 60, 90]


class StartSessionForm(StyledForm):
    domain = forms.ChoiceField(choices=DOMAIN_CHOICES, initial="other")
    course = forms.ModelChoiceField(queryset=Course.objects.filter(archived=False), required=False)
    topic = forms.ModelChoiceField(queryset=Topic.objects.all(), required=False)
    task = forms.ModelChoiceField(queryset=Task.objects.exclude(status__in=["done", "cancelled"]), required=False)
    project = forms.ModelChoiceField(queryset=Project.objects.filter(archived=False), required=False)
    book = forms.ModelChoiceField(queryset=Book.objects.all(), required=False)
    mode = forms.ChoiceField(choices=[("stopwatch", "Stopwatch"), ("countdown", "Countdown"), ("pomodoro", "Pomodoro")], initial="stopwatch")
    countdown_minutes = forms.IntegerField(required=False, min_value=1, initial=25)
    pomodoro_focus_minutes = forms.IntegerField(required=False, min_value=1, initial=25)
    pomodoro_short_break_minutes = forms.IntegerField(required=False, min_value=1, initial=5)
    pomodoro_long_break_minutes = forms.IntegerField(required=False, min_value=1, initial=15)
    pomodoro_cycles = forms.IntegerField(required=False, min_value=1, initial=4)


class CorrectionForm(StyledForm):
    corrected_hours = forms.IntegerField(min_value=0, required=False, initial=0)
    corrected_minutes = forms.IntegerField(min_value=0, max_value=59, required=False, initial=0)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))


class StudyGoalForm(StyledForm):
    period = forms.ChoiceField(choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")])
    target_hours = forms.DecimalField(min_value=0, max_digits=5, decimal_places=1)
