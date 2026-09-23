from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET, require_POST

from apps.core.backup import RestoreError, create_backup, list_backups, restore_backup
from apps.core.export import EXPORTABLE_DATASET_LABELS, EXPORTABLE_DATASETS, export_csv, export_json
from apps.core.forms import (
    AppearanceForm,
    AutoLockForm,
    GeneralSettingsForm,
    OnboardingFinanceForm,
    OnboardingPersonalizeForm,
    OnboardingProfileForm,
    OnboardingProjectForm,
    OnboardingSchoolForm,
    OnboardingSecurityForm,
    PasscodeChangeForm,
)
from apps.core.models import ActivityEvent, Profile, log_activity

ONBOARDING_SESSION_KEY = "onboarding"


class OnboardingStepView(View):
    """Shared shell for every onboarding screen. Each step reads/writes a
    single `request.session[ONBOARDING_SESSION_KEY]` dict — nothing touches
    User/Profile/Account/Project until OnboardingCompleteView commits it all
    in one transaction. So closing LIFEOS at any point mid-wizard leaves
    zero trace in the database; relaunching just starts over at Welcome,
    never a half-created owner or a duplicate Profile (spec: "Interrupted
    onboarding")."""

    form_class = None
    template_name = None
    next_url_name = None

    def dispatch(self, request, *args, **kwargs):
        if Profile.objects.exists():
            return redirect("core:login")
        return super().dispatch(request, *args, **kwargs)

    def data(self, request):
        return request.session.setdefault(ONBOARDING_SESSION_KEY, {})

    def initial(self, request):
        return self.data(request)

    def get(self, request):
        form = self.form_class(initial=self.initial(request)) if self.form_class else None
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if not self.form_class:
            return self.advance(request)
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        self.save_step(request, form)
        return self.advance(request)

    def save_step(self, request, form):
        data = self.data(request)
        data.update(form.cleaned_data)
        request.session.modified = True

    def advance(self, request):
        return redirect(self.next_url_name)


class OnboardingWelcomeView(OnboardingStepView):
    template_name = "core/onboarding/welcome.html"
    next_url_name = "core:onboarding_profile"


class OnboardingProfileView(OnboardingStepView):
    form_class = OnboardingProfileForm
    template_name = "core/onboarding/profile.html"
    next_url_name = "core:onboarding_security"


class OnboardingSecurityView(OnboardingStepView):
    form_class = OnboardingSecurityForm
    template_name = "core/onboarding/security.html"
    next_url_name = "core:onboarding_personalize"

    def initial(self, request):
        return {}  # never pre-fill a passcode field from session state


class OnboardingPersonalizeView(OnboardingStepView):
    form_class = OnboardingPersonalizeForm
    template_name = "core/onboarding/personalize.html"

    def save_step(self, request, form):
        data = self.data(request)
        data["enabled_modules"] = form.enabled_modules()
        request.session.modified = True

    def initial(self, request):
        enabled = self.data(request).get("enabled_modules")
        if enabled is None:
            from apps.core.models import DEFAULT_ENABLED_MODULES

            enabled = DEFAULT_ENABLED_MODULES
        return {key: True for key in enabled}

    def advance(self, request):
        enabled = self.data(request).get("enabled_modules", [])
        if "finance" in enabled:
            return redirect("core:onboarding_finance")
        if "school" in enabled:
            return redirect("core:onboarding_school")
        if "projects" in enabled:
            return redirect("core:onboarding_project")
        return redirect("core:onboarding_complete")


class OnboardingFinanceView(OnboardingStepView):
    form_class = OnboardingFinanceForm
    template_name = "core/onboarding/finance.html"

    def save_step(self, request, form):
        data = self.data(request)
        data.update(form.cleaned_data)
        # Decimal isn't JSON-serializable (the session backend encodes as
        # JSON) — stringify for the trip through the session, parsed back to
        # Decimal in OnboardingCompleteView.
        if data.get("opening_balance") is not None:
            data["opening_balance"] = str(data["opening_balance"])
        request.session.modified = True

    def advance(self, request):
        enabled = self.data(request).get("enabled_modules", [])
        if "school" in enabled:
            return redirect("core:onboarding_school")
        if "projects" in enabled:
            return redirect("core:onboarding_project")
        return redirect("core:onboarding_complete")


class OnboardingSchoolView(OnboardingStepView):
    form_class = OnboardingSchoolForm
    template_name = "core/onboarding/school.html"

    def advance(self, request):
        enabled = self.data(request).get("enabled_modules", [])
        if "projects" in enabled:
            return redirect("core:onboarding_project")
        return redirect("core:onboarding_complete")


class OnboardingProjectView(OnboardingStepView):
    form_class = OnboardingProjectForm
    template_name = "core/onboarding/project.html"
    next_url_name = "core:onboarding_complete"


class OnboardingCompleteView(OnboardingStepView):
    """The only step that ever writes to the database — everything staged
    across the previous screens is committed here, atomically, in one shot."""

    template_name = "core/onboarding/complete.html"

    def get(self, request):
        data = self.data(request)
        if not data.get("password"):
            # Someone jumped straight to this URL without going through
            # Security — never create an owner account with no passcode.
            return redirect("core:onboarding_welcome")

        from apps.core.models import DEFAULT_ENABLED_MODULES
        from apps.finance.models import Account
        from apps.projects.models import Project

        with transaction.atomic():
            user = User.objects.create_user(username="owner", password=data["password"], first_name=data.get("display_name", ""))
            profile = Profile.objects.create(
                user=user,
                display_name=data.get("display_name", ""),
                default_currency=data.get("default_currency", "MAD"),
                theme=data.get("theme", "system"),
                school_name=data.get("school_name", ""),
                enabled_modules=data.get("enabled_modules") or list(DEFAULT_ENABLED_MODULES),
                onboarded_at=timezone.now(),
            )
            if data.get("account_name"):
                try:
                    opening_balance = Decimal(str(data.get("opening_balance") or 0))
                except InvalidOperation:
                    opening_balance = Decimal("0")
                Account.objects.create(
                    name=data["account_name"],
                    account_type=data.get("account_type") or "bank",
                    context="personal",
                    currency=data.get("default_currency", "MAD"),
                    opening_balance=opening_balance,
                )
            if data.get("project_name"):
                Project.objects.create(name=data["project_name"])

        login(request, user)
        log_activity(f"Welcome to LIFEOS, {profile.display_name}", category="system")
        del request.session[ONBOARDING_SESSION_KEY]
        return render(request, self.template_name, {"profile": profile})


@require_GET
def health(request):
    db_status = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_status = "error"
    return JsonResponse({"status": "ok" if db_status == "ok" else "error", "version": settings.LIFEOS_VERSION, "database": db_status})


@method_decorator(login_required, name="dispatch")
class SettingsView(View):
    template_name = "core/settings.html"

    def get(self, request, section="general"):
        from apps.devices.models import SyncConflict

        profile = Profile.objects.get(user=request.user)
        context = {
            "section": section,
            "profile": profile,
            "general_form": GeneralSettingsForm(instance=profile),
            "appearance_form": AppearanceForm(instance=profile),
            "pending_conflict_count": SyncConflict.objects.filter(status="pending").count(),
        }
        if section == "backup":
            context["backups"] = list_backups()
        if section == "export":
            context["datasets"] = EXPORTABLE_DATASETS
            context["dataset_labels"] = EXPORTABLE_DATASET_LABELS
        if section == "security":
            context["passcode_form"] = PasscodeChangeForm(user=request.user)
            context["autolock_form"] = AutoLockForm(instance=profile)
        return render(request, self.template_name, context)

    def post(self, request, section="general"):
        profile = Profile.objects.get(user=request.user)
        if section == "appearance":
            form = AppearanceForm(request.POST, instance=profile)
        elif section == "security":
            form = AutoLockForm(request.POST, instance=profile)
        else:
            form = GeneralSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
        return redirect("core:settings_section", section=section)


@login_required
@require_POST
def passcode_change(request):
    form = PasscodeChangeForm(request.POST, user=request.user)
    if form.is_valid():
        form.save()
        # Without this, changing your own password invalidates the *current*
        # session too (Django checks a password-derived hash on every
        # request) — you'd be correctly logged out mid-flow, which reads as
        # "the app broke" even though the new passcode is fine.
        update_session_auth_hash(request, form.user)
        messages.success(request, "Passcode changed.")
        return redirect("core:settings_section", section="security")

    profile = Profile.objects.get(user=request.user)
    context = {
        "section": "security", "profile": profile, "passcode_form": form,
        "general_form": GeneralSettingsForm(instance=profile), "appearance_form": AppearanceForm(instance=profile),
    }
    return render(request, "core/settings.html", context)


def activity_feed(request):
    events = ActivityEvent.objects.all()[:100]
    return render(request, "core/_activity_feed.html", {"events": events})


@login_required
@require_POST
def activity_ping(request):
    """No-op endpoint the activity heartbeat (static/js/app.js) posts to.
    AutoLockMiddleware does the actual work of refreshing last-activity for
    any non-polling authenticated request — this view just gives real
    mouse/keyboard activity on a page with no other requests in flight
    (e.g. writing in Journal) something to call."""
    return JsonResponse({"ok": True})


@login_required
@require_POST
def backup_create(request):
    backup = create_backup()
    log_activity(f"Created backup ({backup.size_mb} MB)", category="system")
    return redirect("core:settings_section", section="backup")


@login_required
@require_POST
def backup_restore(request, filename):
    try:
        restore_backup(filename)
        log_activity(f"Restored backup {filename}", category="system")
        messages.success(request, f"Restored from {filename}.")
    except RestoreError as exc:
        messages.error(request, str(exc))
    return redirect("core:settings_section", section="backup")


@login_required
@require_GET
def export_download(request, dataset, fmt):
    if dataset not in EXPORTABLE_DATASETS:
        return HttpResponse("Unknown dataset", status=404)
    if fmt == "json":
        content = export_json(dataset)
        content_type = "application/json"
    elif fmt == "csv":
        content = export_csv(dataset)
        content_type = "text/csv"
    else:
        return HttpResponse("Unknown format", status=404)

    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="lifeos_{dataset}.{fmt}"'
    return response
