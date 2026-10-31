from __future__ import annotations

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExamForm, StudyPlanForm, UserSelectForm, VacationForm
from .models import Exam, LearningTask, StudyPlan, Vacation, ensure_tasks_for_user

User = get_user_model()


def ensure_roles():
    Group.objects.get_or_create(name="admin")
    Group.objects.get_or_create(name="supervisor")
    Group.objects.get_or_create(name="user")


def visible_users_for(user: User):
    ensure_roles()
    if user.is_superuser or user.groups.filter(name__in=["admin", "supervisor"]).exists():
        return User.objects.order_by("username")
    return User.objects.filter(pk=user.pk)


def can_view_user(actor: User, target: User) -> bool:
    if actor == target or actor.is_superuser:
        return True
    return actor.groups.filter(name__in=["admin", "supervisor"]).exists()


@login_required
def home(request: HttpRequest) -> HttpResponse:
    return redirect("my")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    target_user = request.user
    user_id = request.GET.get("user")
    if user_id:
        selected = get_object_or_404(User, pk=user_id)
        if not can_view_user(request.user, selected):
            return redirect("my")
        target_user = selected

    today = date.today()
    ensure_tasks_for_user(target_user, today - timedelta(days=7), today + timedelta(days=30))

    open_tasks = LearningTask.objects.filter(
        owner=target_user,
        date=today,
        done=False,
    )
    done_tasks = LearningTask.objects.filter(
        owner=target_user,
        date=today,
        done=True,
    )
    upcoming_exams = Exam.objects.filter(
        owner=target_user,
        exam_date__gte=today,
    ).order_by("exam_date")[:10]

    visible_users = visible_users_for(request.user)
    form = UserSelectForm(visible_users=visible_users, initial={"user": target_user.pk})
    return render(
        request,
        "lernplan/dashboard.html",
        {
            "target_user": target_user,
            "open_tasks": open_tasks,
            "done_tasks": done_tasks,
            "upcoming_exams": upcoming_exams,
            "visible_users": visible_users,
            "user_select_form": form,
            "today": today,
        },
    )


@login_required
def calendar_view(request: HttpRequest) -> HttpResponse:
    target_user = request.user
    user_id = request.GET.get("user")
    if user_id:
        selected = get_object_or_404(User, pk=user_id)
        if not can_view_user(request.user, selected):
            return redirect("calendar")
        target_user = selected

    start = date.today() - timedelta(days=15)
    end = date.today() + timedelta(days=45)

    days = []
    for current in range((end - start).days + 1):
        current_day = start + timedelta(days=current)
        exams = Exam.objects.filter(owner=target_user, exam_date=current_day)
        vacations = Vacation.objects.filter(
            owner=target_user,
            start_date__lte=current_day,
            end_date__gte=current_day,
        )
        tasks = LearningTask.objects.filter(owner=target_user, date=current_day)
        days.append(
            {
                "date": current_day,
                "exams": exams,
                "vacations": vacations,
                "tasks": tasks,
            }
        )

    return render(
        request,
        "lernplan/calendar.html",
        {
            "target_user": target_user,
            "days": days,
            "start": start,
            "end": end,
            "visible_users": visible_users_for(request.user),
        },
    )


@login_required
def day_detail(request: HttpRequest, target_date: str) -> HttpResponse:
    selected_date = date.fromisoformat(target_date)
    target_user = request.user
    user_id = request.GET.get("user")
    if user_id:
        selected = get_object_or_404(User, pk=user_id)
        if not can_view_user(request.user, selected):
            return redirect("calendar")
        target_user = selected

    ensure_tasks_for_user(target_user, selected_date, selected_date)
    tasks = LearningTask.objects.filter(owner=target_user, date=selected_date)
    exams = Exam.objects.filter(owner=target_user, exam_date=selected_date)
    vacations = Vacation.objects.filter(
        owner=target_user,
        start_date__lte=selected_date,
        end_date__gte=selected_date,
    )

    return render(
        request,
        "lernplan/day_detail.html",
        {
            "target_user": target_user,
            "selected_date": selected_date,
            "tasks": tasks,
            "exams": exams,
            "vacations": vacations,
            "visible_users": visible_users_for(request.user),
        },
    )


@login_required
def create_study_plan(request: HttpRequest) -> HttpResponse:
    visible_users = visible_users_for(request.user)
    if request.method == "POST":
        form = StudyPlanForm(request.POST, user=request.user, visible_users=visible_users)
        if form.is_valid():
            form.save()
            messages.success(request, "Lernplan erstellt.")
            return redirect("my")
    else:
        form = StudyPlanForm(user=request.user, visible_users=visible_users)
    return render(
        request,
        "lernplan/study_plan_form.html",
        {"form": form, "title": "Neuer Lernplan"},
    )


@login_required
def edit_study_plan(request: HttpRequest, pk: int) -> HttpResponse:
    plan = get_object_or_404(StudyPlan, pk=pk)
    if not can_view_user(request.user, plan.owner):
        return redirect("my")
    visible_users = visible_users_for(request.user)
    if request.method == "POST":
        form = StudyPlanForm(
            request.POST,
            instance=plan,
            user=request.user,
            visible_users=visible_users,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Lernplan aktualisiert.")
            return redirect("my")
    else:
        form = StudyPlanForm(instance=plan, user=request.user, visible_users=visible_users)
    return render(
        request,
        "lernplan/study_plan_form.html",
        {"form": form, "title": "Lernplan bearbeiten"},
    )


@login_required
def create_exam(request: HttpRequest) -> HttpResponse:
    visible_users = visible_users_for(request.user)
    if request.method == "POST":
        form = ExamForm(request.POST, user=request.user, visible_users=visible_users)
        if form.is_valid():
            exam = form.save()
            messages.success(request, "Prüfung erstellt.")
            ensure_tasks_for_user(
                exam.owner,
                exam.exam_date - timedelta(days=exam.days_before_exam * 2),
                exam.exam_date + timedelta(days=7),
            )
            return redirect("my")
    else:
        form = ExamForm(user=request.user, visible_users=visible_users)
    return render(
        request,
        "lernplan/exam_form.html",
        {"form": form, "title": "Neue Prüfung"},
    )


@login_required
def edit_exam(request: HttpRequest, pk: int) -> HttpResponse:
    exam = get_object_or_404(Exam, pk=pk)
    if not can_view_user(request.user, exam.owner):
        return redirect("my")
    visible_users = visible_users_for(request.user)
    if request.method == "POST":
        form = ExamForm(
            request.POST,
            instance=exam,
            user=request.user,
            visible_users=visible_users,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Prüfung aktualisiert.")
            ensure_tasks_for_user(
                exam.owner,
                exam.exam_date - timedelta(days=exam.days_before_exam * 2),
                exam.exam_date + timedelta(days=7),
            )
            return redirect("my")
    else:
        form = ExamForm(instance=exam, user=request.user, visible_users=visible_users)
    return render(
        request,
        "lernplan/exam_form.html",
        {"form": form, "title": "Prüfung bearbeiten"},
    )


@login_required
def create_vacation(request: HttpRequest) -> HttpResponse:
    visible_users = visible_users_for(request.user)
    if request.method == "POST":
        form = VacationForm(request.POST, user=request.user, visible_users=visible_users)
        if form.is_valid():
            form.save()
            messages.success(request, "Ferien erstellt.")
            return redirect("calendar")
    else:
        form = VacationForm(user=request.user, visible_users=visible_users)
    return render(
        request,
        "lernplan/vacation_form.html",
        {"form": form, "title": "Neue Ferien"},
    )


@login_required
def toggle_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(LearningTask, pk=pk)
    if not can_view_user(request.user, task.owner):
        return redirect("my")
    task.done = not task.done
    task.save(update_fields=["done"])
    return redirect(request.META.get("HTTP_REFERER", "my"))
