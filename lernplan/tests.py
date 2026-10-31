from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Exam, LearningTask, StudyPlan, Vacation, ensure_tasks_for_user

User = get_user_model()


class LernplanModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice")

    def test_admin_can_create_exam_for_other_user(self):
        target_user = User.objects.create_user(username="bob")
        admin = User.objects.create_user(username="admin", is_superuser=True, is_staff=True)

        self.client.force_login(admin)
        response = self.client.post(
            "/exams/new/",
            {
                "owner": target_user.pk,
                "title": "Mündliche Prüfung",
                "subject": "Französisch",
                "exam_date": "2026-02-12",
                "duration_minutes": 45,
                "days_before_exam": 3,
                "content": "Wortschatz üben",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Exam.objects.filter(owner=target_user, subject="Französisch").exists())

    def test_logout_uses_post_and_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post("/logout/")

        self.assertRedirects(response, "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_daily_plan_generates_weekday_tasks(self):
        start_date = date(2026, 1, 5)
        end_date = date(2026, 1, 11)
        StudyPlan.objects.create(
            owner=self.user,
            subject="French",
            duration_minutes=30,
            weekdays=[0, 1, 2, 3, 4],
            active=True,
            overrides_by_vacation=True,
        )

        ensure_tasks_for_user(self.user, start_date, end_date)

        tasks = LearningTask.objects.filter(owner=self.user, source_kind="study_plan")
        self.assertEqual(tasks.count(), 5)
        self.assertTrue(tasks.filter(date=date(2026, 1, 5)).exists())

    def test_exam_generates_preparation_tasks(self):
        exam_date = date(2026, 1, 15)
        Exam.objects.create(
            owner=self.user,
            title="Oral exam",
            subject="French",
            exam_date=exam_date,
            duration_minutes=45,
            days_before_exam=3,
            content="Practice speaking.",
        )

        ensure_tasks_for_user(self.user, date(2026, 1, 10), exam_date)

        exam_tasks = LearningTask.objects.filter(owner=self.user, source_kind="exam")
        self.assertEqual(exam_tasks.count(), 3)
        self.assertTrue(exam_tasks.filter(date=date(2026, 1, 12)).exists())

    def test_vacation_blocks_daily_task_generation(self):
        start_date = date(2026, 2, 2)
        end_date = date(2026, 2, 6)
        StudyPlan.objects.create(
            owner=self.user,
            subject="Math",
            duration_minutes=60,
            weekdays=[0, 1, 2, 3, 4],
            active=True,
            overrides_by_vacation=True,
        )
        Vacation.objects.create(
            owner=self.user,
            name="Winter break",
            start_date=date(2026, 2, 2),
            end_date=date(2026, 2, 6),
        )

        ensure_tasks_for_user(self.user, start_date, end_date)

        self.assertFalse(
            LearningTask.objects.filter(
                owner=self.user,
                source_kind="study_plan",
                date=date(2026, 2, 2),
            ).exists()
        )
