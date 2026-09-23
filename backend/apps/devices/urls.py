from django.urls import path

from apps.devices import views

app_name = "devices"

urlpatterns = [
    path("", views.device_list, name="list"),
    path("pair/", views.device_pair, name="pair"),
    path("pair/<uuid:token_id>/status/", views.device_pair_status, name="pair_status"),
    path("<uuid:pk>/rename/", views.device_rename, name="rename"),
    path("<uuid:pk>/revoke/", views.device_revoke, name="revoke"),
    path("conflicts/", views.sync_conflicts, name="conflicts"),
    path("conflicts/<uuid:pk>/resolve/", views.sync_conflict_resolve, name="conflict_resolve"),
]
