from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import log_activity
from apps.devices.models import Device, PairingToken, SyncConflict
from apps.devices.services import local_lan_ip, pairing_qr_data_uri


@login_required
def device_list(request):
    devices = Device.objects.filter(revoked=False)
    return render(request, "devices/list.html", {"active_nav": "devices", "devices": devices})


@login_required
def device_pair(request):
    pairing_token = PairingToken.issue()
    qr_data_uri = pairing_qr_data_uri(pairing_token)
    context = {
        "active_nav": "devices",
        "pairing_token": pairing_token,
        "qr_data_uri": qr_data_uri,
        "lifetime_seconds": PairingToken.LIFETIME_SECONDS,
        # Manual fallback for when the camera can't scan (spec §73: "provide
        # fallback manual IP/endpoint if discovery fails") — same host/port/
        # token the QR encodes, just also readable as plain text.
        "manual_host": local_lan_ip(),
        "manual_port": 8420,
    }
    return render(request, "devices/pair.html", context)


@login_required
def device_pair_status(request, token_id):
    pairing_token = get_object_or_404(PairingToken, pk=token_id)
    if pairing_token.used_by_device:
        return JsonResponse({"paired": True, "device_name": pairing_token.used_by_device.name})
    if not pairing_token.is_valid:
        return JsonResponse({"paired": False, "expired": True})
    return JsonResponse({"paired": False, "expired": False})


@login_required
def device_rename(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == "POST":
        new_name = request.POST.get("name", "").strip()
        if new_name:
            device.name = new_name
            device.save(update_fields=["name"])
    return redirect("devices:list")


@login_required
def device_revoke(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == "POST":
        device.revoke()
        log_activity(f"Revoked device {device.name}", category="devices", obj=device)
    return redirect("devices:list")


def _conflict_model_and_serializer(entity_type):
    if entity_type == "transaction":
        from apps.finance.api import TransactionSerializer
        from apps.finance.models import Transaction

        return Transaction, TransactionSerializer
    if entity_type == "journal_entry":
        from apps.journal.api import JournalEntrySerializer
        from apps.journal.models import JournalEntry

        return JournalEntry, JournalEntrySerializer
    if entity_type == "chapter":
        from apps.writing.api import ChapterSerializer
        from apps.writing.models import Chapter

        return Chapter, ChapterSerializer
    if entity_type == "study_session":
        from apps.study.api import StudySessionSerializer
        from apps.study.models import StudySession

        return StudySession, StudySessionSerializer
    raise ValueError(f"Unknown conflict entity_type: {entity_type}")


def _conflict_display(entity_type, data):
    """A short, human summary of a conflict's data — `data` is either a
    model instance (the current Mac record) or a plain dict (the device's
    rejected payload). Just enough for someone to tell the two apart, not a
    full diff — see docs/SYNC.md "Conflicts"."""

    def get(key):
        return data.get(key) if isinstance(data, dict) else getattr(data, key, None)

    if entity_type == "transaction":
        amount, currency, description = get("amount"), get("currency"), get("description")
        return f"{amount or '?'} {currency or ''} — {description or '(no description)'}".strip()
    if entity_type == "journal_entry":
        title = get("title") or "(untitled entry)"
        body = (get("body") or "").strip()
        snippet = f"{body[:60]}…" if len(body) > 60 else body
        return f"{title} — {snippet}" if snippet else title
    if entity_type == "chapter":
        return get("title") or "(untitled chapter)"
    if entity_type == "study_session":
        seconds = get("corrected_duration_seconds")
        reason = get("correction_reason") or ""
        return f"{seconds}s — {reason}".strip(" —") if seconds is not None else "(no correction)"
    return str(data)


@login_required
def sync_conflicts(request):
    conflicts = SyncConflict.objects.filter(status="pending").select_related("device")
    rows = []
    for conflict in conflicts:
        model, _serializer = _conflict_model_and_serializer(conflict.entity_type)
        instance = model.objects.filter(pk=conflict.entity_id).first()
        rows.append({
            "conflict": conflict,
            "local_summary": _conflict_display(conflict.entity_type, conflict.local_data),
            "server_summary": _conflict_display(conflict.entity_type, instance) if instance else "(deleted on the Mac)",
            "instance_exists": instance is not None,
        })
    return render(request, "devices/conflicts.html", {"active_nav": "devices", "rows": rows})


@login_required
@require_POST
def sync_conflict_resolve(request, pk):
    conflict = get_object_or_404(SyncConflict, pk=pk, status="pending")
    action = request.POST.get("action")
    model, serializer_class = _conflict_model_and_serializer(conflict.entity_type)

    if action == "keep_mac":
        conflict.resolve("resolved_server")
        messages.success(request, "Kept the Mac's version. The device's change was discarded.")
    elif action == "keep_local":
        instance = model.objects.filter(pk=conflict.entity_id).first()
        if instance is None:
            messages.error(request, "That record no longer exists on the Mac — can't apply the device's change.")
        else:
            serializer = serializer_class(instance, data=conflict.local_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                conflict.resolve("resolved_local")
                messages.success(request, "Applied the device's version over the Mac's.")
            else:
                messages.error(request, "The device's data no longer fits this record; couldn't apply it.")
    elif action == "keep_both":
        serializer = serializer_class(data=conflict.local_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            conflict.resolve("resolved_both")
            messages.success(request, "Kept both — the device's change was saved as a new record.")
        else:
            messages.error(request, "The device's data couldn't be saved as a new record.")

    return redirect("devices:conflicts")
