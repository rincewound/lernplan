from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import models, transaction

User = get_user_model()


class StudyPlan(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="study_plans")
    subject = models.CharField(max_length=120)
    duration_minutes = models.PositiveIntegerField(default=30)
    weekdays = models.JSONField(default=list, blank=True)
    effective_from = models.DateField(default=date.today)
    effective_until = models.DateField(null=True, blank=True)
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

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.effective_until and self.effective_until < self.effective_from:
            raise ValidationError(
                {"effective_until": "Das Enddatum muss am oder nach dem Startdatum liegen."}
            )

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.pk:
            previous = StudyPlan.objects.filter(pk=self.pk).first()
            if previous:
                _ensure_study_plan_tasks(
                    previous,
                    previous.effective_from,
                    date.today() - timedelta(days=1),
                )
                LearningTask.objects.filter(
                    source_kind="study_plan",
                    source_id=self.pk,
                    date__gte=date.today(),
                ).delete()
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        _ensure_study_plan_tasks(self, self.effective_from, date.today() - timedelta(days=1))
        LearningTask.objects.filter(
            source_kind="study_plan",
            source_id=self.pk,
            date__gte=date.today(),
        ).delete()
        return super().delete(*args, **kwargs)

    def is_active_on_day(self, target_day: date) -> bool:
        return target_day.weekday() in [int(day) for day in self.weekdays]

    def is_valid_on_day(self, target_day: date) -> bool:
        return (
            self.active
            and self.effective_from <= target_day
            and (self.effective_until is None or target_day <= self.effective_until)
        )

    @property
    def weekday_names(self) -> list[str]:
        names = [
            "Montag",
            "Dienstag",
            "Mittwoch",
            "Donnerstag",
            "Freitag",
            "Samstag",
            "Sonntag",
        ]
        return [names[int(day)] for day in self.weekdays]

    def has_vacation_overlap(self, target_day: date) -> bool:
        return Vacation.objects.filter(
            users=self.owner,
            start_date__lte=target_day,
            end_date__gte=target_day,
        ).exists()


class Vacation(models.Model):
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    users = models.ManyToManyField(User, related_name="vacations", blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="created_vacations",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["start_date", "name"]

    def __str__(self) -> str:
        return self.name

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


def _ensure_study_plan_tasks(plan: StudyPlan, start_date: date, end_date: date):
    start_date = max(start_date, plan.effective_from)
    if plan.effective_until:
        end_date = min(end_date, plan.effective_until)
    if not plan.active or end_date < start_date:
        return

    for current_day in date_range(start_date, end_date):
        if not plan.is_active_on_day(current_day):
            continue
        if plan.overrides_by_vacation and plan.has_vacation_overlap(current_day):
            if current_day >= date.today():
                LearningTask.objects.filter(
                    owner=plan.owner,
                    date=current_day,
                    source_kind="study_plan",
                    source_id=plan.pk,
                ).delete()
            continue
        LearningTask.objects.get_or_create(
            owner=plan.owner,
            date=current_day,
            source_kind="study_plan",
            source_id=plan.pk,
            defaults={
                "subject": plan.subject,
                "title": f"{plan.subject} study block",
                "minutes": plan.duration_minutes,
            },
        )


def ensure_tasks_for_user(user: User, start_date: date, end_date: date):
    for plan in StudyPlan.objects.filter(owner=user, active=True):
        _ensure_study_plan_tasks(plan, start_date, end_date)

    for exam in Exam.objects.filter(owner=user):
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
