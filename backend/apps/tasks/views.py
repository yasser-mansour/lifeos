from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.models import log_activity
from apps.tasks.forms import TaskForm, WaitingForm
from apps.tasks.models import OPEN_STATUSES, Task
from apps.tasks.services import task_focus_summary


def _scoped_queryset(view, qs):
    today = timezone.localdate()
    if view == "inbox":
        return qs.filter(status="inbox")
    if view == "today":
        return qs.filter(status__in=OPEN_STATUSES).filter(due_date=today)
    if view == "upcoming":
        return qs.filter(status__in=OPEN_STATUSES).filter(due_date__gt=today)
    if view == "overdue":
        return qs.filter(status__in=["todo", "in_progress"], due_date__lt=today)
    if view == "waiting":
        return qs.filter(status="waiting")
    if view == "completed":
        return qs.filter(status="done")
    if view == "all":
        return qs.filter(status__in=OPEN_STATUSES)
    return qs.filter(status__in=OPEN_STATUSES)


@login_required
def task_list(request):
    view = request.GET.get("view") or request.GET.get("status") or "today"
    project_id = request.GET.get("project")
    course_id = request.GET.get("course")
    person_id = request.GET.get("person")

    tasks = Task.objects.select_related("project", "course", "person")
    tasks = _scoped_queryset(view, tasks)
    if project_id:
        tasks = tasks.filter(project_id=project_id)
    if course_id:
        tasks = tasks.filter(course_id=course_id)
    if person_id:
        tasks = tasks.filter(person_id=person_id)

    counts = {
        "inbox": Task.objects.filter(status="inbox").count(),
        "today": _scoped_queryset("today", Task.objects.all()).count(),
        "upcoming": _scoped_queryset("upcoming", Task.objects.all()).count(),
        "overdue": _scoped_queryset("overdue", Task.objects.all()).count(),
        "waiting": Task.objects.filter(status="waiting").count(),
        "all": Task.objects.filter(status__in=OPEN_STATUSES).count(),
    }

    # Create-in-context: a "New Task" link from a Project/Course/Person page
    # passes its id here so the new-task form actually opens pre-selecting
    # that parent, instead of a blank form that only happens to sit on a
    # filtered list (see study.views.start for the pattern this mirrors).
    initial = {}
    if project_id:
        initial["project"] = project_id
    if course_id:
        initial["course"] = course_id
    if person_id:
        initial["person"] = person_id

    context = {
        "active_nav": "tasks",
        "tasks": tasks,
        "view": view,
        "counts": counts,
        "form": TaskForm(initial=initial),
        "show_new": request.GET.get("new") == "1",
        "prefill_context": bool(initial),
    }
    return render(request, "tasks/list.html", context)


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            log_activity(f"Added task: {task.title}", category="tasks", obj=task)
    redirect_view = request.POST.get("next_view", "today")
    return redirect(f"/tasks/?view={redirect_view}")


@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            log_activity(f"Updated task: {task.title}", category="tasks", obj=task)
    context = {"task": task, "waiting_form": WaitingForm(instance=task), "edit_form": TaskForm(instance=task), **task_focus_summary(task)}
    return render(request, "tasks/_detail_panel.html", context)


@login_required
def task_complete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        if task.status == "done":
            task.status = "todo"
            task.completed_at = None
            task.save(update_fields=["status", "completed_at"])
        else:
            task.mark_done()
            log_activity(f"Completed task: {task.title}", category="tasks", obj=task)
    next_url = request.POST.get("next", "")
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect("tasks:list")


@login_required
def task_detail_panel(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        waiting_form = WaitingForm(request.POST, instance=task)
        if waiting_form.is_valid():
            task = waiting_form.save(commit=False)
            task.status = "waiting"
            task.save()
    context = {"task": task, "waiting_form": WaitingForm(instance=task), "edit_form": TaskForm(instance=task), **task_focus_summary(task)}
    return render(request, "tasks/_detail_panel.html", context)


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    context = {"active_nav": "tasks", "task": task, "waiting_form": WaitingForm(instance=task), "edit_form": TaskForm(instance=task), **task_focus_summary(task)}
    return render(request, "tasks/detail.html", context)
