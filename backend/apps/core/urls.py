from django.contrib.auth import views as auth_views
from django.urls import path

from apps.core import views
from apps.core.forms import OwnerLoginForm

app_name = "core"

urlpatterns = [
    path("first-run/", views.OnboardingWelcomeView.as_view(), name="onboarding_welcome"),
    path("first-run/profile/", views.OnboardingProfileView.as_view(), name="onboarding_profile"),
    path("first-run/security/", views.OnboardingSecurityView.as_view(), name="onboarding_security"),
    path("first-run/personalize/", views.OnboardingPersonalizeView.as_view(), name="onboarding_personalize"),
    path("first-run/finance/", views.OnboardingFinanceView.as_view(), name="onboarding_finance"),
    path("first-run/school/", views.OnboardingSchoolView.as_view(), name="onboarding_school"),
    path("first-run/project/", views.OnboardingProjectView.as_view(), name="onboarding_project"),
    path("first-run/complete/", views.OnboardingCompleteView.as_view(), name="onboarding_complete"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html", authentication_form=OwnerLoginForm), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("settings/<str:section>/", views.SettingsView.as_view(), name="settings_section"),
    path("activity/", views.activity_feed, name="activity_feed"),
    path("activity/ping/", views.activity_ping, name="activity_ping"),
    path("settings/security/passcode/", views.passcode_change, name="passcode_change"),
    path("backup/create/", views.backup_create, name="backup_create"),
    path("backup/<str:filename>/restore/", views.backup_restore, name="backup_restore"),
    path("export/<str:dataset>.<str:fmt>", views.export_download, name="export_download"),
]
