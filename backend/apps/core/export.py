"""Data export — the user owns their data (spec §95). JSON exports are
complete and structured; CSV exports cover the record types people
actually want in a spreadsheet."""

import csv
import io
import json
from decimal import Decimal


def _json_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def export_json(dataset_name: str) -> str:
    data = _collect(dataset_name)
    return json.dumps(data, indent=2, default=_json_default)


def export_csv(dataset_name: str) -> str:
    rows = _collect(dataset_name)
    buffer = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _json_default(v) if isinstance(v, Decimal) else v for k, v in row.items()})
    return buffer.getvalue()


def _collect(dataset_name: str) -> list[dict]:
    from apps.finance.models import Account, Transaction
    from apps.goals.models import Goal
    from apps.journal.models import JournalEntry
    from apps.projects.models import Project
    from apps.study.models import StudySession
    from apps.tasks.models import Task
    from apps.writing.models import Book, Chapter

    if dataset_name == "accounts":
        return [
            {"id": str(a.id), "name": a.name, "context": a.context, "currency": a.currency, "opening_balance": a.opening_balance, "balance": a.balance}
            for a in Account.objects.all()
        ]
    if dataset_name == "transactions":
        return [
            {
                "id": str(t.id), "account": t.account.name, "amount": t.amount, "currency": t.currency, "type": t.type,
                "date": t.date, "category": t.category.name if t.category else "", "description": t.description,
            }
            for t in Transaction.objects.select_related("account", "category").all()
        ]
    if dataset_name == "study_sessions":
        return [
            {
                "id": str(s.id), "course": s.course.name if s.course else "", "mode": s.mode, "status": s.status,
                "started_at": s.started_at, "ended_at": s.ended_at, "duration_seconds": s.duration_seconds,
            }
            for s in StudySession.objects.select_related("course").all()
        ]
    if dataset_name == "tasks":
        return [
            {"id": str(t.id), "title": t.title, "status": t.status, "priority": t.priority, "due_date": t.due_date, "project": t.project.name if t.project else ""}
            for t in Task.objects.select_related("project").all()
        ]
    if dataset_name == "projects":
        return [{"id": str(p.id), "name": p.name, "area": p.area, "status": p.status} for p in Project.objects.all()]
    if dataset_name == "journal":
        return [{"id": str(j.id), "date": j.date, "title": j.title, "body": j.body, "mood": j.mood} for j in JournalEntry.objects.all()]
    if dataset_name == "writing":
        rows = []
        for book in Book.objects.all():
            for chapter in book.chapters.all():
                rows.append({"book": book.title, "chapter": chapter.title, "order": chapter.order, "word_count": chapter.word_count, "content": chapter.content})
        return rows
    if dataset_name == "goals":
        return [{"id": str(g.id), "title": g.title, "goal_type": g.goal_type, "target_value": g.target_value, "current_value": g.current_value, "status": g.status} for g in Goal.objects.all()]

    raise ValueError(f"Unknown dataset: {dataset_name}")


EXPORTABLE_DATASETS = ["accounts", "transactions", "study_sessions", "tasks", "projects", "journal", "writing", "goals"]

EXPORTABLE_DATASET_LABELS = {
    "accounts": "Accounts",
    "transactions": "Transactions",
    "study_sessions": "Study Sessions",
    "tasks": "Tasks",
    "projects": "Projects",
    "journal": "Journal",
    "writing": "Writing",
    "goals": "Goals",
}
