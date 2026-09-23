from django.urls import path

from apps.school import views

app_name = "school"

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("create/", views.course_create, name="course_create"),
    path("<uuid:pk>/", views.course_detail, name="course_detail"),
    path("<uuid:pk>/edit/", views.course_update, name="course_update"),
    path("<uuid:course_pk>/topics/create/", views.topic_create, name="topic_create"),
    path("<uuid:course_pk>/topics/<uuid:pk>/edit/", views.topic_update, name="topic_update"),
    path("<uuid:course_pk>/topics/<uuid:pk>/delete/", views.topic_delete, name="topic_delete"),
    path("exams/create/", views.exam_create, name="exam_create"),
    path("exams/<uuid:pk>/edit/", views.exam_update, name="exam_update"),
    path("exams/<uuid:pk>/delete/", views.exam_delete, name="exam_delete"),
]
