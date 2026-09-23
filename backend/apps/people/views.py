from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.models import log_activity
from apps.people.forms import OrganizationForm, PersonForm
from apps.people.models import RELATIONSHIP_CHOICES, Organization, Person
from apps.people.services import organization_summary, person_summary


@login_required
def person_list(request):
    """People & Organizations (spec §2/§11) — one combined, filterable list
    rather than two separate pages: the spec's own filter set (People /
    Organizations / Clients / Service Providers / Family / ...) reads as
    facets of one list, not a reason to split it in two."""
    query = request.GET.get("q", "")
    type_filter = request.GET.get("type", "")  # "person" | "organization" | ""
    relationship_filter = request.GET.get("relationship", "")

    people_qs = Person.objects.all()
    orgs_qs = Organization.objects.filter(archived=False)
    if query:
        people_qs = people_qs.filter(Q(name__icontains=query) | Q(organization__icontains=query) | Q(email__icontains=query))
        orgs_qs = orgs_qs.filter(Q(name__icontains=query) | Q(website__icontains=query) | Q(email__icontains=query))

    people_list = list(people_qs)
    orgs_list = list(orgs_qs)
    if relationship_filter:
        people_list = [p for p in people_list if relationship_filter in p.relationship_types]
        orgs_list = [o for o in orgs_list if relationship_filter in o.relationship_types]

    entries = []
    if type_filter != "organization":
        entries += [{"kind": "person", "obj": p} for p in people_list]
    if type_filter != "person":
        entries += [{"kind": "organization", "obj": o} for o in orgs_list]
    entries.sort(key=lambda e: e["obj"].name.lower())

    return render(
        request,
        "people/list.html",
        {
            "active_nav": "people",
            "entries": entries,
            "query": query,
            "type_filter": type_filter,
            "relationship_filter": relationship_filter,
            "relationship_choices": RELATIONSHIP_CHOICES,
            "show_new": request.GET.get("new") == "1",
            "show_new_org": request.GET.get("new_org") == "1",
            "form": PersonForm(),
            "org_form": OrganizationForm(),
        },
    )


@login_required
def person_create(request):
    if request.method == "POST":
        form = PersonForm(request.POST)
        if form.is_valid():
            person = form.save()
            log_activity(f"Added {person.name} to People & Organizations", category="people", obj=person)
    return redirect("people:list")


@login_required
def person_detail_panel(request, pk):
    person = get_object_or_404(Person, pk=pk)
    context = {"person": person, "edit_form": PersonForm(instance=person), **person_summary(person)}
    return render(request, "people/_detail_panel.html", context)


@login_required
def person_detail(request, pk):
    person = get_object_or_404(Person, pk=pk)
    context = {"active_nav": "people", "person": person, "edit_form": PersonForm(instance=person), **person_summary(person)}
    return render(request, "people/detail.html", context)


@login_required
def person_update(request, pk):
    person = get_object_or_404(Person, pk=pk)
    if request.method == "POST":
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            log_activity(f"Updated {person.name}", category="people", obj=person)
    context = {"person": person, "edit_form": PersonForm(instance=person), **person_summary(person)}
    return render(request, "people/_detail_panel.html", context)


@login_required
def person_delete(request, pk):
    person = get_object_or_404(Person, pk=pk)
    if request.method == "POST":
        person.soft_delete()
        log_activity(f"Removed {person.name} from People", category="people")
    return redirect("people:list")


@login_required
def person_link_project(request, pk):
    person = get_object_or_404(Person, pk=pk)
    if request.method == "POST":
        project_id = request.POST.get("project_id")
        if project_id:
            person.projects.add(project_id)
            log_activity(f"Linked {person.name} to a project", category="people", obj=person)
    return redirect("people:detail", pk=pk)


@login_required
def person_unlink_project(request, pk, project_id):
    person = get_object_or_404(Person, pk=pk)
    if request.method == "POST":
        person.projects.remove(project_id)
    return redirect("people:detail", pk=pk)


# ---------------------------------------------------------------------------
# Organizations — same shape as the Person views above, on purpose (spec
# §49: full CRUD parity between the two entity types).
# ---------------------------------------------------------------------------


@login_required
def org_create(request):
    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
            org = form.save()
            log_activity(f"Added {org.name} to People & Organizations", category="people", obj=org)
    return redirect("people:list")


@login_required
def org_detail_panel(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    context = {"org": org, "edit_form": OrganizationForm(instance=org), **organization_summary(org)}
    return render(request, "people/_org_detail_panel.html", context)


@login_required
def org_detail(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    context = {"active_nav": "people", "org": org, "edit_form": OrganizationForm(instance=org), **organization_summary(org)}
    return render(request, "people/org_detail.html", context)


@login_required
def org_update(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        form = OrganizationForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            log_activity(f"Updated {org.name}", category="people", obj=org)
    context = {"org": org, "edit_form": OrganizationForm(instance=org), **organization_summary(org)}
    return render(request, "people/_org_detail_panel.html", context)


@login_required
def org_archive_toggle(request, pk):
    """Archive is the low-drama, reversible action (spec §46/§82: "Prefer
    Archive" over delete for anything with real history) — a plain boolean
    flip, completely separate from BaseModel's soft_delete()/deleted_at,
    which `org_delete` below still uses for the deliberate, harder-to-miss
    "actually remove this" path."""
    org = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        org.archived = not org.archived
        org.save(update_fields=["archived"])
        log_activity(f"{'Archived' if org.archived else 'Restored'} {org.name}", category="people")
    return redirect("people:org_detail", pk=pk)


@login_required
def org_delete(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        # Transactions keep their organization_id (SET_NULL only fires if
        # the row is ever hard-deleted, which nothing in this app does) —
        # soft-deleting the Organization removes it from lists/pickers
        # without touching a single linked Transaction (spec §82).
        org.soft_delete()
        log_activity(f"Removed {org.name} from People & Organizations", category="people")
    return redirect("people:list")


@login_required
def org_link_project(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        project_id = request.POST.get("project_id")
        if project_id:
            org.projects.add(project_id)
            log_activity(f"Linked {org.name} to a project", category="people", obj=org)
    return redirect("people:org_detail", pk=pk)


@login_required
def org_unlink_project(request, pk, project_id):
    org = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        org.projects.remove(project_id)
    return redirect("people:org_detail", pk=pk)
