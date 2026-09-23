from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.models import log_activity
from apps.journal.forms import JournalEntryForm
from apps.journal.models import JournalEntry


@login_required
def entry_list(request):
    query = request.GET.get("q", "")
    entries = JournalEntry.objects.all()
    if query:
        entries = entries.filter(Q(title__icontains=query) | Q(body__icontains=query))
    project_id = request.GET.get("project")
    if project_id:
        entries = entries.filter(project_id=project_id)
    goal_id = request.GET.get("goal")
    if goal_id:
        entries = entries.filter(goal_id=goal_id)
    return render(request, "journal/list.html", {"active_nav": "journal", "entries": entries, "query": query})


@login_required
def entry_new(request):
    entry = JournalEntry.objects.create()
    log_activity("Started a new journal entry", category="journal", obj=entry)
    return redirect("journal:detail", pk=entry.pk)


@login_required
def entry_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    context = {
        "active_nav": "journal", "entry": entry, "form": JournalEntryForm(instance=entry),
        "back_url": reverse("journal:list"), "back_label": "Journal",
    }
    return render(request, "journal/detail.html", context)


@login_required
@require_POST
def entry_autosave(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    form = JournalEntryForm(request.POST, instance=entry)
    if form.is_valid():
        form.save()
        return JsonResponse({"status": "saved"})
    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    if request.method == "POST":
        entry.soft_delete()
    return redirect("journal:list")
