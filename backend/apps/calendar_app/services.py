from django.utils import timezone


def today_agenda():
    """Unifies tasks due today, calendar events today, and exams today into
    one chronological list for the Home dashboard's Today section (spec
    §14) — items with a time sort first, timeless items fall under Anytime."""
    from apps.calendar_app.models import Event
    from apps.school.models import Exam
    from apps.tasks.models import Task

    today = timezone.localdate()
    items = []

    for event in Event.objects.filter(start__date=today):
        items.append({
            "time": None if event.all_day else timezone.localtime(event.start).strftime("%H:%M"),
            "sort_key": "00:00" if event.all_day else timezone.localtime(event.start).strftime("%H:%M"),
            "title": event.title,
            "meta": "Event" + (f" · {event.location}" if event.location else ""),
            "url": "",
        })

    for task in Task.objects.filter(due_date=today).exclude(status__in=["done", "cancelled"]):
        items.append({
            "time": task.due_time.strftime("%H:%M") if task.due_time else None,
            "sort_key": task.due_time.strftime("%H:%M") if task.due_time else "23:59",
            "title": task.title,
            "meta": "Task" + (f" · {task.project.name}" if task.project else ""),
            "url": task.get_absolute_url(),
        })

    for exam in Exam.objects.filter(date=today):
        items.append({
            "time": exam.time.strftime("%H:%M") if exam.time else None,
            "sort_key": exam.time.strftime("%H:%M") if exam.time else "23:59",
            "title": f"{exam.course.name} exam",
            "meta": "Exam" + (f" · {exam.location}" if exam.location else ""),
            "url": exam.course.get_absolute_url(),
        })

    items.sort(key=lambda i: i["sort_key"])
    return items
