from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.models import log_activity
from apps.projects.forms import ProjectForm
from apps.projects.models import Project
from apps.projects.services import project_summary


@login_required
def project_list(request):
    area = request.GET.get("area", "")
    projects = Project.objects.filter(archived=False)
    if area:
        projects = projects.filter(area=area)
    return render(
        request,
        "projects/list.html",
        {
            "active_nav": "projects", "projects": projects, "area": area,
            "form": ProjectForm(initial={"status": "active", "priority": "normal", "area": "personal"}),
            "show_new": request.GET.get("new") == "1",
        },
    )


@login_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            log_activity(f"Created project {project.name}", category="projects", obj=project)
            return redirect("projects:detail", pk=project.pk)
    return redirect("projects:list")


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tab = request.GET.get("tab", "overview")
    context = {"active_nav": "projects", "project": project, "tab": tab, "edit_form": ProjectForm(instance=project), **project_summary(project)}
    if tab == "people":
        from apps.people.models import Person

        context["available_people"] = Person.objects.exclude(pk__in=project.people.values_list("pk", flat=True))
    return render(request, "projects/detail.html", context)


@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            log_activity(f"Updated project {project.name}", category="projects", obj=project)
    return redirect(f"{reverse('projects:detail', args=[pk])}?tab=overview")


@login_required
def project_link_person(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        person_id = request.POST.get("person_id")
        if person_id:
            project.people.add(person_id)
            log_activity(f"Linked a person to {project.name}", category="projects", obj=project)
    return redirect(f"{reverse('projects:detail', args=[pk])}?tab=people")


@login_required
def project_unlink_person(request, pk, person_id):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        project.people.remove(person_id)
    return redirect(f"{reverse('projects:detail', args=[pk])}?tab=people")
