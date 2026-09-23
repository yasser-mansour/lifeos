from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.models import log_activity
from apps.inbox.models import InboxItem


@login_required
def inbox_list(request):
    items = InboxItem.objects.filter(processed=False)
    return render(request, "inbox/list.html", {"active_nav": "inbox", "items": items, "show_new": request.GET.get("new") == "1"})


@login_required
def capture(request):
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            InboxItem.objects.create(content=content)
    return redirect("inbox:list")


@login_required
def convert_to_task(request, pk):
    item = get_object_or_404(InboxItem, pk=pk)
    if request.method == "POST":
        from apps.tasks.models import Task

        task = Task.objects.create(title=item.content, status="inbox")
        item.processed = True
        item.converted_to = "task"
        item.converted_at = timezone.now()
        item.save(update_fields=["processed", "converted_to", "converted_at"])
        log_activity(f"Converted inbox item to task: {task.title}", category="inbox", obj=task)
    return redirect("inbox:list")


@login_required
def convert_to_note(request, pk):
    item = get_object_or_404(InboxItem, pk=pk)
    if request.method == "POST":
        from apps.notes.models import Note

        note = Note.objects.create(title=item.content[:80], content=item.content)
        item.processed = True
        item.converted_to = "note"
        item.converted_at = timezone.now()
        item.save(update_fields=["processed", "converted_to", "converted_at"])
    return redirect("inbox:list")


@login_required
def dismiss(request, pk):
    item = get_object_or_404(InboxItem, pk=pk)
    if request.method == "POST":
        item.processed = True
        item.converted_to = "dismissed"
        item.converted_at = timezone.now()
        item.save(update_fields=["processed", "converted_to", "converted_at"])
    return redirect("inbox:list")
