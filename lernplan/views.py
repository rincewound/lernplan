from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
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


def can_manage_vacation(actor: User, vacation: Vacation) -> bool:
    if actor.is_superuser or actor.groups.filter(name__in=["admin", "supervisor"]).exists():
        return True
    return (
        vacation.created_by_id == actor.pk
        and vacation.users.count() == 1
        and vacation.users.filter(pk=actor.pk).exists()
    )


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
        exam_date__lte=today + timedelta(days=21),
    ).order_by("exam_date")

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

    today = date.today()
    month_value = request.GET.get("month")
    try:
        month_start = (
            date.fromisoformat(f"{month_value}-01") if month_value else today.replace(day=1)
        )
    except ValueError:
        return HttpResponseBadRequest("Ungültiger Monat.")
    if month_start.day != 1:
        return HttpResponseBadRequest("Ungültiger Monat.")
    month_end = date(
        month_start.year,
        month_start.month,
        calendar.monthrange(month_start.year, month_start.month)[1],
    )
    previous_month = (month_start - timedelta(days=1)).replace(day=1)
    next_month = (month_end + timedelta(days=1)).replace(day=1)
    start = month_start
    end = month_end
    ensure_tasks_for_user(target_user, start, end)

    days = []
    for current in range((end - start).days + 1):
        current_day = start + timedelta(days=current)
        exams = Exam.objects.filter(owner=target_user, exam_date=current_day)
        vacations = Vacation.objects.filter(
            users=target_user,
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
                "task_count": tasks.count(),
                "done_task_count": tasks.filter(done=True).count(),
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
            "month": month_start,
            "previous_month": previous_month,
            "next_month": next_month,
            "selected_user": target_user,
            "user_select_form": UserSelectForm(
                visible_users=visible_users_for(request.user),
                initial={"user": target_user.pk},
            ),
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
        users=target_user,
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
def study_plans(request: HttpRequest) -> HttpResponse:
    target_user = request.user
    user_id = request.GET.get("user")
    if user_id:
        selected = get_object_or_404(User, pk=user_id)
        if not can_view_user(request.user, selected):
            return redirect("study_plans")
        target_user = selected
    plans = StudyPlan.objects.filter(owner=target_user)
    return render(
        request,
        "lernplan/study_plans.html",
        {
            "target_user": target_user,
            "plans": plans,
            "visible_users": visible_users_for(request.user),
            "user_select_form": UserSelectForm(
                visible_users=visible_users_for(request.user),
                initial={"user": target_user.pk},
            ),
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
def delete_study_plan(request: HttpRequest, pk: int) -> HttpResponse:
    plan = get_object_or_404(StudyPlan, pk=pk)
    if not can_view_user(request.user, plan.owner):
        return redirect("study_plans")
    if request.method == "POST":
        plan.delete()
        messages.success(request, "Lernplan gelöscht. Vergangene Lerneinheiten bleiben erhalten.")
        return redirect("study_plans")
    return render(request, "lernplan/study_plan_confirm_delete.html", {"plan": plan})


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
def vacations(request: HttpRequest) -> HttpResponse:
    visible_users = visible_users_for(request.user)
    can_manage_all = request.user.is_superuser or request.user.groups.filter(
        name__in=["admin", "supervisor"]
    ).exists()
    if can_manage_all:
        vacation_list = Vacation.objects.all()
    else:
        vacation_list = Vacation.objects.filter(
            Q(created_by=request.user) | Q(users=request.user)
        ).distinct()
    vacation_list = list(vacation_list.prefetch_related("users"))
    for vacation in vacation_list:
        vacation.can_manage = can_manage_vacation(request.user, vacation)
    return render(
        request,
        "lernplan/vacations.html",
        {
            "vacations": vacation_list,
            "visible_users": visible_users,
        },
    )


@login_required
def create_vacation(request: HttpRequest) -> HttpResponse:
    visible_users = visible_users_for(request.user)
    if request.method == "POST":
        form = VacationForm(request.POST, user=request.user, visible_users=visible_users)
        if form.is_valid():
            vacation = form.save()
            if not (request.user.is_superuser or request.user.groups.filter(
                name__in=["admin", "supervisor"]
            ).exists()):
                vacation.users.set([request.user])
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
def edit_vacation(request: HttpRequest, pk: int) -> HttpResponse:
    vacation = get_object_or_404(Vacation, pk=pk)
    if not can_manage_vacation(request.user, vacation):
        return redirect("vacations")
    visible_users = visible_users_for(request.user)
    if request.method == "POST":
        form = VacationForm(
            request.POST,
            instance=vacation,
            user=request.user,
            visible_users=visible_users,
        )
        if form.is_valid():
            saved_vacation = form.save()
            if not (request.user.is_superuser or request.user.groups.filter(
                name__in=["admin", "supervisor"]
            ).exists()):
                saved_vacation.users.set([request.user])
            messages.success(request, "Ferien aktualisiert.")
            return redirect("vacations")
    else:
        form = VacationForm(
            instance=vacation,
            user=request.user,
            visible_users=visible_users,
        )
    return render(
        request,
        "lernplan/vacation_form.html",
        {"form": form, "title": "Ferien bearbeiten"},
    )


@login_required
def delete_vacation(request: HttpRequest, pk: int) -> HttpResponse:
    vacation = get_object_or_404(Vacation, pk=pk)
    if not can_manage_vacation(request.user, vacation):
        return redirect("vacations")
    if request.method == "POST":
        vacation.delete()
        messages.success(request, "Ferien gelöscht.")
        return redirect("vacations")
    return render(
        request,
        "lernplan/vacation_confirm_delete.html",
        {"vacation": vacation},
    )


@login_required
def toggle_task(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(LearningTask, pk=pk)
    if not can_view_user(request.user, task.owner):
        return redirect("my")
    task.done = not task.done
    task.save(update_fields=["done"])
    return redirect(request.META.get("HTTP_REFERER", "my"))
