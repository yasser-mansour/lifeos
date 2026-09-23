from django.utils.dateparse import parse_datetime
from rest_framework.response import Response

from apps.devices.auth import request_device
from apps.devices.models import SyncConflict


class DeletionAwareSyncMixin:
    """Mix into a ModelViewSet so a device's incremental pull can tell "this
    row changed" apart from "this row was deleted" — without either, a
    record soft-deleted on the Mac (see BaseModel.soft_delete) simply
    vanishes from the default queryset and a device that already has a
    local copy never finds out; it just keeps showing a "deleted" record
    forever (spec §39).

    Opt-in and additive: with no ``modified_since`` query param the
    endpoint behaves exactly as before (active rows only, via the model's
    default manager). Passing ``modified_since=<ISO 8601 timestamp>``
    switches to ``all_objects`` filtered to ``updated_at >= modified_since``
    (soft-delete bumps updated_at like any other save), so the response
    includes recently-deleted rows too — the serializer's ``deleted`` field
    (added alongside this mixin on each entity) tells the client which is
    which.
    """

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        modified_since = self.request.query_params.get("modified_since")
        if not modified_since:
            return model.objects.all()
        since = parse_datetime(modified_since)
        qs = model.all_objects.all()
        return qs.filter(updated_at__gte=since) if since else qs


class ConflictAwareUpdateMixin:
    """Mix into a ModelViewSet to park a device's stale update as a
    SyncConflict instead of overwriting a record that moved on since the
    device last saw it (see docs/SYNC.md "Conflicts").

    Only device-originated requests (Android etc., via
    DeviceTokenAuthentication) that include a "version" in their payload are
    checked — desktop web-UI edits go through SessionAuthentication, carry
    no "version" field, and are unaffected, so this can't regress the
    primary editing path. A device that omits "version" is also let through
    unchecked, matching every push payload that predates this feature.

    Set ``conflict_entity_type`` to one of apps.devices.models.CONFLICT_ENTITY_CHOICES
    on the subclass.
    """

    conflict_entity_type = None

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        device = request_device(request)
        incoming_version = request.data.get("version")

        if device is not None and incoming_version is not None:
            try:
                incoming_version = int(incoming_version)
            except (TypeError, ValueError):
                incoming_version = None

            if incoming_version is not None and incoming_version < instance.version:
                SyncConflict.objects.create(
                    entity_type=self.conflict_entity_type,
                    entity_id=instance.id,
                    device=device,
                    local_data=dict(request.data),
                    server_version=instance.version,
                    local_version=incoming_version,
                )
                return Response({"detail": "This record changed on the Mac since your device last saw it.", "conflict": True}, status=409)

        return super().update(request, *args, **kwargs)
