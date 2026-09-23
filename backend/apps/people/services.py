from django.utils import timezone


def person_summary(person):
    """Cross-app aggregation for the Person detail page. Imports are local
    to avoid a hard module-load-time dependency between people/projects/
    finance/tasks — those apps optionally reference Person, not vice versa."""
    from apps.finance.services import counterparty_summary
    from apps.projects.models import Project
    from apps.tasks.models import Task

    linked_projects = Project.objects.filter(people=person)
    financial = counterparty_summary(person=person)

    return {
        "financial": financial,
        "projects": linked_projects,
        "available_projects": Project.objects.filter(archived=False).exclude(pk__in=linked_projects.values_list("pk", flat=True)),
        "open_tasks": Task.objects.filter(person=person).exclude(status__in=["done", "cancelled"]),
        "upcoming_events": person.events.filter(start__gte=timezone.now())[:5],
    }


def organization_summary(organization):
    """The Organization-side equivalent of person_summary — same shape
    (Finance V2 spec §10: Overview / Finance / Projects / Tasks / Notes /
    Activity), minus tasks/events, which nothing links an Organization to
    yet (only Person carries a `person` FK on Task/Event)."""
    from apps.finance.services import counterparty_summary
    from apps.projects.models import Project

    linked_projects = Project.objects.filter(organizations=organization)
    financial = counterparty_summary(organization=organization)

    return {
        "financial": financial,
        "projects": linked_projects,
        "available_projects": Project.objects.filter(archived=False).exclude(pk__in=linked_projects.values_list("pk", flat=True)),
    }
