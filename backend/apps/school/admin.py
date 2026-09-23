from django.contrib import admin

from apps.school.models import Course, Exam, Topic


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "teacher", "active", "archived")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "order")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("course", "date", "importance")
    date_hierarchy = "date"
