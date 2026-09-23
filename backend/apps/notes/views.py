from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import log_activity
from apps.notes.forms import NoteForm
from apps.notes.models import Note


@login_required
def note_list(request):
    query = request.GET.get("q", "")
    notes = Note.objects.all()
    if query:
        notes = notes.filter(Q(title__icontains=query) | Q(content__icontains=query))
    return render(request, "notes/list.html", {"active_nav": "notes", "notes": notes, "query": query})


@login_required
def note_new(request):
    # Create-in-context: a "New Note" link from a Project/Task/Person/
    # Course/Goal page passes its id so the note starts out actually linked
    # to where it was opened from, instead of a blank, unrelated note.
    fields = {}
    for key in ("project", "task", "person", "course", "goal"):
        value = request.GET.get(key)
        if value:
            fields[f"{key}_id"] = value
    note = Note.objects.create(**fields)
    log_activity("Created a note", category="notes", obj=note)
    return redirect("notes:detail", pk=note.pk)


@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk)
    return render(request, "notes/detail.html", {"active_nav": "notes", "note": note, "form": NoteForm(instance=note)})


@login_required
@require_POST
def note_autosave(request, pk):
    note = get_object_or_404(Note, pk=pk)
    form = NoteForm(request.POST, instance=note)
    if form.is_valid():
        form.save()
        return JsonResponse({"status": "saved"})
    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@login_required
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        note.soft_delete()
    return redirect("notes:list")
