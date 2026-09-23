from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.models import log_activity
from apps.goals.forms import GoalForm, GoalProgressForm
from apps.goals.models import Goal


@login_required
def goal_list(request):
    goals = Goal.objects.filter(status="active")

    # Create-in-context: "New Goal" from a Project/Course page pre-selects
    # that parent (see study.views.start for the pattern this mirrors).
    project_id = request.GET.get("project")
    course_id = request.GET.get("course")
    initial = {}
    if project_id:
        initial["project"] = project_id
    if course_id:
        initial["course"] = course_id

    context = {
        "active_nav": "goals", "goals": goals, "form": GoalForm(initial=initial),
        "show_new": request.GET.get("new") == "1", "prefill_context": bool(initial),
    }
    return render(request, "goals/list.html", context)


@login_required
def goal_create(request):
    if request.method == "POST":
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save()
            log_activity(f"Set a new goal: {goal.title}", category="goals", obj=goal)
    return redirect("goals:list")


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    context = {"active_nav": "goals", "goal": goal, "edit_form": GoalForm(instance=goal)}
    return render(request, "goals/detail.html", context)


@login_required
def goal_update(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            log_activity(f"Updated goal: {goal.title}", category="goals", obj=goal)
    return redirect("goals:detail", pk=pk)


@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == "POST":
        goal.soft_delete()
        log_activity(f"Removed goal: {goal.title}", category="goals")
    return redirect("goals:list")


@login_required
def goal_update_progress(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == "POST":
        form = GoalProgressForm(request.POST, instance=goal)
        if form.is_valid():
            goal = form.save(commit=False)
            if goal.target_value and goal.current_value >= goal.target_value:
                goal.status = "completed"
            goal.save()
    next_url = request.POST.get("next", "")
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect("goals:list")
