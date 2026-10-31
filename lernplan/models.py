from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class StudyPlan(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="study_plans")
    subject = models.CharField(max_length=120)
    duration_minutes = models.PositiveIntegerField(default=30)
    weekdays = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)
    overrides_by_vacation = models.BooleanField(
        default=True,
        help_text="Hide tasks during vacations.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subject", "created_at"]

    def __str__(self) -> str:
        return f"{self.subject} ({self.owner})"

    def is_active_on_day(self, target_day: date) -> bool:
        return target_day.weekday() in [int(day) for day in self.weekdays]

    @property
    def weekday_names(self) -> list[str]:
        names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        return [names[int(day)] for day in self.weekdays]

    def has_vacation_overlap(self, target_day: date) -> bool:
        return self.owner.vacations.filter(
            start_date__lte=target_day,
            end_date__gte=target_day,
        ).exists()


class Vacation(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vacations")
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ["start_date", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.owner})"

    def contains(self, target_day: date) -> bool:
        return self.start_date <= target_day <= self.end_date


class Exam(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exams")
    title = models.CharField(max_length=160)
    subject = models.CharField(max_length=120)
    exam_date = models.DateField()
    duration_minutes = models.PositiveIntegerField(default=30)
    days_before_exam = models.PositiveIntegerField(default=3)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["exam_date", "subject"]

    def __str__(self) -> str:
        return f"{self.subject}: {self.title}"

    def task_dates(self, start: date | None = None, end: date | None = None):
        if not start:
            start = date.today() - timedelta(days=30)
        if not end:
            end = date.today() + timedelta(days=90)
        for offset in range(1, self.days_before_exam + 1):
            candidate = self.exam_date - timedelta(days=offset)
            if start <= candidate <= end:
                yield candidate


class LearningTask(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="learning_tasks")
    subject = models.CharField(max_length=120)
    title = models.CharField(max_length=180)
    date = models.DateField()
    minutes = models.PositiveIntegerField(default=30)
    done = models.BooleanField(default=False)
    source_kind = models.CharField(
        max_length=20,
        choices=[("study_plan", "Study plan"), ("exam", "Exam")],
    )
    source_id = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "subject"]
        unique_together = ("owner", "date", "source_kind", "source_id")

    def __str__(self) -> str:
        return f"{self.subject} on {self.date}"


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def ensure_tasks_for_user(user: User, start_date: date, end_date: date):
    for plan in StudyPlan.objects.filter(owner=user, active=True):
        for current_day in date_range(start_date, end_date):
            if not plan.is_active_on_day(current_day):
                continue
            if plan.overrides_by_vacation and Vacation.objects.filter(
                owner=user,
                start_date__lte=current_day,
                end_date__gte=current_day,
            ).exists():
                continue
            LearningTask.objects.get_or_create(
                owner=user,
                date=current_day,
                source_kind="study_plan",
                source_id=plan.pk,
                defaults={
                    "subject": plan.subject,
                    "title": f"{plan.subject} study block",
                    "minutes": plan.duration_minutes,
                },
            )

    for exam in Exam.objects.filter(owner=user, exam_date__gte=start_date, exam_date__lte=end_date):
        for task_date in exam.task_dates(start_date, end_date):
            LearningTask.objects.get_or_create(
                owner=user,
                date=task_date,
                source_kind="exam",
                source_id=exam.pk,
                defaults={
                    "subject": exam.subject,
                    "title": f"{exam.title} preparation",
                    "minutes": exam.duration_minutes,
                },
            )
