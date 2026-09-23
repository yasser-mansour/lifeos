from django.contrib import admin

from apps.devices.models import Device, DeviceCredential, PairingToken


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "platform", "device_type", "status", "last_seen", "last_sync", "revoked")
    list_filter = ("platform", "status", "revoked")


@admin.register(DeviceCredential)
class DeviceCredentialAdmin(admin.ModelAdmin):
    list_display = ("device", "active", "created_at")


@admin.register(PairingToken)
class PairingTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "expires_at", "used_at", "used_by_device")
