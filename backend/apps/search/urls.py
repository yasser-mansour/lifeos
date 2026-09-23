from django.urls import path

from apps.search import views

app_name = "search"

urlpatterns = [
    path("api/", views.search_api, name="api"),
]
