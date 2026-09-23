from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.models import log_activity
from apps.school.forms import CourseForm, ExamForm, TopicForm
from apps.school.models import IMPORTANCE_CHOICES, Course, Exam, Topic


@login_required
def course_list(request):
    courses = Course.objects.filter(archived=False)
    return render(request, "school/list.html", {"active_nav": "study", "courses": courses, "form": CourseForm(), "show_new": request.GET.get("new") == "1"})


@login_required
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            log_activity(f"Added course {course.name}", category="school", obj=course)
            return redirect("school:course_detail", pk=course.pk)
    return redirect("school:course_list")


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    from apps.study.services import course_study_stats

    context = {
        "active_nav": "study",
        "course": course,
        "topics": course.topics.all(),
        "exams": course.exams.filter(date__gte=timezone.localdate()),
        "goals": course.goals.filter(status="active"),
        "upcoming_events": course.events.filter(start__gte=timezone.now())[:5],
        "topic_form": TopicForm(),
        "exam_form": ExamForm(initial={"course": course}),
        "edit_form": CourseForm(instance=course),
        "all_courses": Course.objects.filter(archived=False),
        "importance_choices": IMPORTANCE_CHOICES,
        "stats": course_study_stats(course),
    }
    return render(request, "school/course_detail.html", context)


@login_required
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            log_activity(f"Updated course {course.name}", category="school", obj=course)
    return redirect("school:course_detail", pk=pk)


@login_required
def topic_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if request.method == "POST":
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.course = course
            topic.save()
    return redirect("school:course_detail", pk=course_pk)


@login_required
def topic_update(request, course_pk, pk):
    topic = get_object_or_404(Topic, pk=pk, course_id=course_pk)
    if request.method == "POST":
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
    return redirect("school:course_detail", pk=course_pk)


@login_required
def topic_delete(request, course_pk, pk):
    topic = get_object_or_404(Topic, pk=pk, course_id=course_pk)
    if request.method == "POST":
        topic.soft_delete()
    return redirect("school:course_detail", pk=course_pk)


@login_required
def exam_create(request):
    if request.method == "POST":
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            log_activity(f"Added exam for {exam.course.name}", category="school", obj=exam)
            return redirect("school:course_detail", pk=exam.course_id)
    return redirect("school:course_list")


@login_required
def exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            exam = form.save()
            log_activity(f"Updated exam for {exam.course.name}", category="school", obj=exam)
    return redirect("school:course_detail", pk=exam.course_id)


@login_required
def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    course_pk = exam.course_id
    if request.method == "POST":
        exam.soft_delete()
    return redirect("school:course_detail", pk=course_pk)
