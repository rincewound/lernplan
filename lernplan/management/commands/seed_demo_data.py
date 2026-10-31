from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from lernplan.models import Exam, StudyPlan, Vacation, ensure_tasks_for_user

User = get_user_model()


class Command(BaseCommand):
    help = "Create demo users and data for the learning plan app."

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name="admin")
        supervisor_group, _ = Group.objects.get_or_create(name="supervisor")
        user_group, _ = Group.objects.get_or_create(name="user")

        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
        admin_user.groups.set([admin_group, supervisor_group, user_group])

        user, _ = User.objects.get_or_create(username="learner")
        user.set_password("learner123")
        user.save()
        user.groups.add(user_group)

        StudyPlan.objects.update_or_create(
            owner=user,
            subject="French",
            defaults={
                "duration_minutes": 30,
                "weekdays": [0, 1, 2, 3, 4],
                "active": True,
                "overrides_by_vacation": True,
            },
        )

        Vacation.objects.update_or_create(
            owner=user,
            name="School holidays",
            defaults={
                "start_date": date.today() + timedelta(days=10),
                "end_date": date.today() + timedelta(days=18),
            },
        )

        Exam.objects.update_or_create(
            owner=user,
            title="Speaking exam",
            subject="French",
            defaults={
                "exam_date": date.today() + timedelta(days=12),
                "duration_minutes": 40,
                "days_before_exam": 4,
                "content": "Prepare vocabulary and spoken phrases.",
            },
        )

        start = date.today() - timedelta(days=7)
        end = date.today() + timedelta(days=30)
        ensure_tasks_for_user(user, start, end)
        self.stdout.write(self.style.SUCCESS("Demo data created."))
