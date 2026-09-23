import hashlib
import secrets
import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel

CONFLICT_ENTITY_CHOICES = [
    ("transaction", "Transaction"),
    ("journal_entry", "Journal Entry"),
    ("chapter", "Writing Chapter"),
    ("study_session", "Study Session"),
]


class Device(BaseModel):
    PLATFORM_CHOICES = [("macos", "macOS"), ("android", "Android"), ("web", "Web")]
    TYPE_CHOICES = [("primary", "Primary"), ("mobile", "Mobile"), ("other", "Other")]
    STATUS_CHOICES = [("online", "Online"), ("offline", "Offline"), ("revoked", "Revoked")]

    name = models.CharField(max_length=100)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    device_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="other")
    model = models.CharField(max_length=100, blank=True, default="")
    app_version = models.CharField(max_length=20, blank=True, default="")
    paired_at = models.DateTimeField(default=timezone.now)
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="offline")
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen"]

    def __str__(self):
        return self.name

    def touch(self):
        self.last_seen = timezone.now()
        self.status = "online"
        self.save(update_fields=["last_seen", "status"])

    def revoke(self):
        self.revoked = True
        self.revoked_at = timezone.now()
        self.status = "revoked"
        self.save(update_fields=["revoked", "revoked_at", "status"])
        DeviceCredential.objects.filter(device=self).update(active=False)


def _hash_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_pairing_token():
    return secrets.token_urlsafe(24)


class DeviceCredential(models.Model):
    """A long-lived API token issued to a device after successful pairing.
    Only the hash is stored — the raw token is shown once, at pairing time."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name="credential")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, device: Device):
        raw_token = secrets.token_urlsafe(32)
        cls.objects.filter(device=device).delete()
        cls.objects.create(device=device, token_hash=_hash_secret(raw_token))
        return raw_token

    @classmethod
    def authenticate(cls, raw_token: str):
        if not raw_token:
            return None
        token_hash = _hash_secret(raw_token)
        try:
            credential = cls.objects.select_related("device").get(token_hash=token_hash, active=True)
        except cls.DoesNotExist:
            return None
        if credential.device.revoked:
            return None
        return credential.device


class PairingToken(models.Model):
    """Short-lived, single-use token embedded in the Mac's pairing QR code.
    It never grants lasting access by itself — it only lets a scanning device
    exchange it, once, for a real DeviceCredential (see docs/DEVICES.md)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=64, unique=True, db_index=True, default=_generate_pairing_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    used_by_device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL)

    LIFETIME_SECONDS = 120

    @classmethod
    def issue(cls):
        return cls.objects.create(expires_at=timezone.now() + timezone.timedelta(seconds=cls.LIFETIME_SECONDS))

    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at

    def consume(self, device: Device):
        self.used_at = timezone.now()
        self.used_by_device = device
        self.save(update_fields=["used_at", "used_by_device"])


class SyncConflict(BaseModel):
    """A device pushed an update to a record that had already moved on
    (BaseModel.version on the server was ahead of the version the device
    last saw). Rather than silently pick a winner, we park the device's
    payload here for a human to resolve from Settings > Sync > Conflicts —
    see docs/SYNC.md "Conflicts" and spec §80. Deliberately not a CRDT: the
    three resolutions are keep-local, keep-server, or keep-both-as-a-copy."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("resolved_local", "Kept Local"),
        ("resolved_server", "Kept Mac"),
        ("resolved_both", "Kept Both"),
    ]

    entity_type = models.CharField(max_length=30, choices=CONFLICT_ENTITY_CHOICES)
    entity_id = models.UUIDField()
    device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name="sync_conflicts")
    local_data = models.JSONField(default=dict)
    server_version = models.PositiveIntegerField()
    local_version = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_entity_type_display()} conflict ({self.status})"

    def resolve(self, status):
        self.status = status
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])
