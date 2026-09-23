from django.urls import path

from apps.finance import views

app_name = "finance"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("context/<str:context>/", views.context_detail, name="context_detail"),
    path("accounts/create/", views.account_create, name="account_create"),
    path("accounts/<uuid:pk>/", views.account_detail, name="account_detail"),
    path("accounts/<uuid:pk>/edit/", views.account_update, name="account_update"),
    path("accounts/<uuid:pk>/delete/", views.account_delete, name="account_delete"),
    path("transactions/new/", views.transaction_new, name="transaction_new"),
    path("transactions/<uuid:pk>/edit/", views.transaction_edit, name="transaction_edit"),
    path("transactions/<uuid:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("transfer/new/", views.transfer_new, name="transfer_new"),
    path("transfer/<uuid:pk>/edit/", views.transfer_edit, name="transfer_edit"),
    path("transfer/<uuid:pk>/delete/", views.transfer_delete, name="transfer_delete"),
    path("all-activity/", views.all_activity_view, name="all_activity"),
    path("recurring/", views.recurring_list, name="recurring_list"),
    path("recurring/<uuid:pk>/edit/", views.recurring_edit, name="recurring_edit"),
    path("recurring/<uuid:pk>/delete/", views.recurring_delete, name="recurring_delete"),
    path("recurring/<uuid:pk>/record/", views.recurring_record_actual, name="recurring_record"),
    path("funds/", views.fund_list, name="fund_list"),
    path("funds/create/", views.fund_create, name="fund_create"),
    path("funds/<uuid:pk>/", views.fund_detail, name="fund_detail"),
    path("funds/<uuid:pk>/edit/", views.fund_update, name="fund_update"),
    path("funds/<uuid:pk>/archive/", views.fund_archive_toggle, name="fund_archive_toggle"),
    path("funds/<uuid:pk>/delete/", views.fund_delete, name="fund_delete"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/archive/", views.category_archive_toggle, name="category_archive_toggle"),
    path("reclassify/", views.reclassify, name="reclassify"),
    path("reclassify/<uuid:pk>/map-to-fund/", views.reclassify_map_to_fund, name="reclassify_map_to_fund"),
]
