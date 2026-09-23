from django.urls import path

from apps.writing import views

app_name = "writing"

urlpatterns = [
    path("", views.library, name="library"),
    path("books/create/", views.book_create, name="book_create"),
    path("books/<uuid:pk>/", views.book_detail, name="book_detail"),
    path("books/<uuid:book_pk>/chapters/create/", views.chapter_create, name="chapter_create"),
    path("books/<uuid:book_pk>/chapters/reorder/", views.chapter_reorder, name="chapter_reorder"),
    path("chapters/<uuid:pk>/", views.chapter_edit, name="chapter_edit"),
    path("chapters/<uuid:pk>/autosave/", views.chapter_autosave, name="chapter_autosave"),
    path("chapters/<uuid:pk>/delete/", views.chapter_delete, name="chapter_delete"),
]
