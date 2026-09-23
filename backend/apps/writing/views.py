import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import log_activity
from apps.writing.forms import BookForm, ChapterForm
from apps.writing.models import Book, Chapter


@login_required
def library(request):
    books = Book.objects.all()
    return render(request, "writing/library.html", {"active_nav": "writing", "books": books, "form": BookForm(), "show_new": request.GET.get("new") == "1"})


@login_required
def book_create(request):
    if request.method == "POST":
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()
            log_activity(f"Started writing project {book.title}", category="writing", obj=book)
            return redirect("writing:book_detail", pk=book.pk)
    return redirect("writing:library")


@login_required
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, "writing/book_detail.html", {"active_nav": "writing", "book": book, "chapters": book.chapters.all()})


@login_required
def chapter_create(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    next_order = book.chapters.count()
    chapter = Chapter.objects.create(book=book, order=next_order, title=f"Chapter {next_order + 1}")
    return redirect("writing:chapter_edit", pk=chapter.pk)


@login_required
def chapter_edit(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    context = {
        "active_nav": "writing",
        "chapter": chapter,
        "book": chapter.book,
        "chapters": chapter.book.chapters.all(),
        "form": ChapterForm(instance=chapter),
    }
    return render(request, "writing/chapter_edit.html", context)


@login_required
@require_POST
def chapter_autosave(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    form = ChapterForm(request.POST, instance=chapter)
    if form.is_valid():
        form.save()
        return JsonResponse({"status": "saved", "word_count": chapter.word_count})
    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@login_required
@require_POST
def chapter_reorder(request, book_pk):
    order = json.loads(request.body or "{}").get("order", [])
    for index, chapter_id in enumerate(order):
        Chapter.objects.filter(pk=chapter_id, book_id=book_pk).update(order=index)
    return JsonResponse({"status": "ok"})


@login_required
def chapter_delete(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    book_pk = chapter.book_id
    if request.method == "POST":
        chapter.soft_delete()
    return redirect("writing:book_detail", pk=book_pk)
