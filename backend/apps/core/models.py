import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


#: Every toggleable module a fresh install's onboarding can enable/disable
#: (spec: distribution onboarding "Personalization" step). Tasks/Focus/
#: Finance/Projects/People/Notes are on by default; School/Journal/Writing/
#: Calendar/Goals start off so a new user's nav isn't cluttered with things
#: they haven't said they want yet. Turning a module off only hides its nav
#: entry (see templates/layout/_sidebar.html) — it never deletes data, so
#: re-enabling it later shows everything exactly as it was left.
ALL_MODULES = ["tasks", "focus", "finance", "projects", "people", "notes", "school", "journal", "writing", "calendar", "goals"]
DEFAULT_ENABLED_MODULES = ["tasks", "focus", "finance", "projects", "people", "notes"]


def default_enabled_modules():
    # The MODEL default is deliberately "everything on" — it only ever
    # applies to a row that didn't go through onboarding explicitly (a
    # migration backfilling this field onto an existing installation's
    # Profile). An existing user must never have a module they're already
    # using silently vanish from their sidebar. The smaller, curated
    # DEFAULT_ENABLED_MODULES set is applied explicitly by the onboarding
    # wizard itself (apps.core.views.OnboardingCompleteView) for brand-new
    # installs only.
    return list(ALL_MODULES)


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class ActiveManager(models.Manager):
    """Default manager: hides soft-deleted rows so a stray FK never resurrects
    something the user threw away, without ever truly losing the row."""

    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    """Common ancestor for every LIFEOS domain model.

    UUID primary keys so records are globally identifiable across devices
    without coordination (required for sync). ``version`` is bumped on every
    update for optimistic-concurrency / sync-conflict detection. Deletion is
    soft by default — financial, journal and study history must never
    silently disappear (see docs/SYNC.md and docs/DATABASE.md).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now, editable=False)
    version = models.PositiveIntegerField(default=1, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        self.updated_at = timezone.now()
        if not is_new:
            self.version = (self.version or 1) + 1
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"updated_at", "version"}
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    def delete(self, *args, **kwargs):
        # Django's default .delete() is a hard delete. Every existing
        # deletion path in this codebase calls soft_delete() explicitly —
        # but a generic path (e.g. DRF's default ModelViewSet.destroy(),
        # used by the Android API) calls the plain instance .delete(), and
        # would otherwise permanently destroy financial/journal/study
        # history the moment a mobile client's delete button was wired up.
        # Soft-delete by default; hard_delete() is the explicit escape
        # hatch for real cleanup (management commands, admin tooling).
        self.soft_delete()

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class Profile(models.Model):
    """The single LIFEOS owner. One row, created during first-run setup."""

    THEME_CHOICES = [("light", "Light"), ("dark", "Dark"), ("system", "System")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lifeos_profile")
    display_name = models.CharField(max_length=100)
    default_currency = models.CharField(max_length=3, default="MAD")
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="system")
    school_name = models.CharField(max_length=150, blank=True, default="")
    enabled_modules = models.JSONField(default=default_enabled_modules)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    safe_to_spend_horizon_days = models.PositiveIntegerField(default=30)
    safe_to_spend_reserve = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 0 means "lock immediately" — see apps.core.middleware.AutoLockMiddleware.
    # "Lock when LIFEOS closes" is not a setting here: it's a structural
    # guarantee (SESSION_EXPIRE_AT_BROWSER_CLOSE) rather than something a
    # user could casually switch off — see spec §49.
    auto_lock_minutes = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ActivityEvent(models.Model):
    """Lightweight append-only log powering the global Recent Activity feed.

    Deliberately not a BaseModel (no soft delete / sync version needed for a
    log) and never stores sensitive payloads (card numbers, tokens, message
    bodies) — see settings.LOGGING and docs/SECURITY.md.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    verb = models.CharField(max_length=255)
    category = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=50, blank=True, default="")
    object_id = models.UUIDField(null=True, blank=True)
    device_name = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.verb


def log_activity(verb, category, obj=None, device_name=""):
    ActivityEvent.objects.create(
        verb=verb,
        category=category,
        object_type=obj.__class__.__name__ if obj is not None else "",
        object_id=getattr(obj, "id", None),
        device_name=device_name,
    )
