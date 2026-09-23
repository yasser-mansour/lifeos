from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from apps.devices.models import Device, DeviceCredential, PairingToken, SyncConflict


class DeviceSerializer(serializers.ModelSerializer):
    # Lets a device's own Sync/Diagnostics screen show "N conflicts need
    # your attention" without a separate endpoint — see spec §71/§44:
    # financial/journal conflicts must be surfaced, never silently resolved.
    pending_conflicts = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ["id", "name", "platform", "device_type", "model", "app_version", "paired_at", "first_seen", "last_seen", "last_sync", "status", "revoked", "pending_conflicts"]
        read_only_fields = ["id", "paired_at", "first_seen", "last_seen", "last_sync", "status", "revoked", "pending_conflicts"]

    def get_pending_conflicts(self, obj):
        return SyncConflict.objects.filter(device=obj, status="pending").count()


class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeviceSerializer
    queryset = Device.objects.filter(revoked=False)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def claim_device(request):
    """The only endpoint an unpaired device can reach. It trades a short-
    lived, single-use PairingToken (scanned from the Mac's QR code) for a
    real long-lived device credential — see docs/DEVICES.md."""
    token_value = request.data.get("pairing_token", "")
    pairing_token = PairingToken.objects.filter(token=token_value).first()
    if not pairing_token or not pairing_token.is_valid:
        return Response({"detail": "This pairing code is invalid or has expired. Generate a new one on the Mac."}, status=status.HTTP_400_BAD_REQUEST)

    device = Device.objects.create(
        name=request.data.get("device_name", "New Device"),
        platform=request.data.get("platform", "android"),
        device_type="mobile",
        model=request.data.get("model", ""),
        app_version=request.data.get("app_version", ""),
        paired_at=timezone.now(),
        first_seen=timezone.now(),
        last_seen=timezone.now(),
        status="online",
    )
    raw_token = DeviceCredential.issue(device)
    pairing_token.consume(device)

    return Response({
        "device_id": str(device.id),
        "device_token": raw_token,
    }, status=status.HTTP_201_CREATED)
