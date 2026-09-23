from django.db import migrations


def classify_existing_sessions(apps, schema_editor):
    """Conservative, deterministic classification only — see spec §5/§21:
    "Do not invent meaning." A session already linked to a Course or Topic
    is unambiguously SCHOOL. A session linked only to a Project inherits
    that project's own area (Project.area is already exactly
    business/school/personal — no guessing needed). Anything else
    (no course/topic/project at all) is left as OTHER rather than forced
    into a domain the data doesn't actually support — those show up in the
    "Needs classification" filter for the user to resolve by hand."""
    StudySession = apps.get_model("study", "StudySession")
    for session in StudySession.objects.all().iterator():
        if session.course_id or session.topic_id:
            domain = "school"
        elif session.project_id:
            area = session.project.area
            domain = area if area in ("business", "school", "personal") else "other"
        else:
            domain = "other"
        if domain != session.domain:
            StudySession.objects.filter(pk=session.pk).update(domain=domain)


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0002_studysession_book_studysession_domain"),
    ]

    operations = [
        migrations.RunPython(classify_existing_sessions, migrations.RunPython.noop),
    ]
