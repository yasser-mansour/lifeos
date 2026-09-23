from django.db import models

from apps.core.models import BaseModel

IMPORTANCE_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]


class Course(BaseModel):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    teacher = models.CharField(max_length=100, blank=True, default="")
    color = models.CharField(max_length=7, default="#4954E0")
    active = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("school:course_detail", args=[self.pk])


class Topic(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=150)
    order = models.PositiveIntegerField(default=0, blank=True)

    class Meta:
        ordering = ["course", "order", "name"]

    def __str__(self):
        return f"{self.course.name} / {self.name}"


class Exam(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exams")
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=150, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    importance = models.CharField(max_length=10, choices=IMPORTANCE_CHOICES, default="medium")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["date", "time"]

    def __str__(self):
        return f"{self.course.name} exam — {self.date}"
