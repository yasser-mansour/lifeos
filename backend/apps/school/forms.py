from django import forms

from apps.core.base_forms import StyledModelForm
from apps.school.models import Course, Exam, Topic


class CourseForm(StyledModelForm):
    class Meta:
        model = Course
        fields = ["name", "teacher", "color", "description"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class TopicForm(StyledModelForm):
    class Meta:
        model = Topic
        fields = ["name", "order"]


class ExamForm(StyledModelForm):
    class Meta:
        model = Exam
        fields = ["course", "date", "time", "location", "description", "importance", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "time": forms.TimeInput(attrs={"type": "time"})}
