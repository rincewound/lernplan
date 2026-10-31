from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
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

    def test_seed_demo_data_preserves_existing_vacation_assignments(self):
        learner = User.objects.create_user(username="learner")
        vacation = Vacation.objects.create(
            name="School holidays",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 14),
        )
        vacation.users.add(self.user, learner)

        call_command("seed_demo_data", stdout=None)

        self.assertSetEqual(
            set(vacation.users.values_list("pk", flat=True)),
            {self.user.pk, learner.pk},
        )

    def test_seed_demo_data_does_not_reset_existing_learner_password(self):
        learner = User.objects.create_user(username="learner", password="user-chosen-password")

        call_command("seed_demo_data", stdout=None)

        learner.refresh_from_db()
        self.assertTrue(learner.check_password("user-chosen-password"))

    def test_daily_plan_generates_weekday_tasks(self):
        start_date = date(2026, 1, 5)
        end_date = date(2026, 1, 11)
        StudyPlan.objects.create(
            owner=self.user,
            subject="French",
            duration_minutes=30,
            weekdays=[0, 1, 2, 3, 4],
            effective_from=start_date,
            active=True,
            overrides_by_vacation=True,
        )

        ensure_tasks_for_user(self.user, start_date, end_date)

        tasks = LearningTask.objects.filter(owner=self.user, source_kind="study_plan")
        self.assertEqual(tasks.count(), 5)
        self.assertTrue(tasks.filter(date=date(2026, 1, 5)).exists())

    def test_plan_validity_dates_bound_generated_tasks(self):
        start_date = date(2026, 1, 5)
        end_date = date(2026, 1, 11)
        StudyPlan.objects.create(
            owner=self.user,
            subject="Chemie",
            duration_minutes=25,
            weekdays=[0, 1, 2, 3, 4, 5, 6],
            effective_from=date(2026, 1, 7),
            effective_until=date(2026, 1, 9),
        )

        ensure_tasks_for_user(self.user, start_date, end_date)

        tasks = LearningTask.objects.filter(owner=self.user, source_kind="study_plan")
        self.assertEqual(set(tasks.values_list("date", flat=True)), {
            date(2026, 1, 7),
            date(2026, 1, 8),
            date(2026, 1, 9),
        })

    def test_editing_plan_preserves_past_task_values_and_updates_future(self):
        today = date.today()
        plan = StudyPlan.objects.create(
            owner=self.user,
            subject="Biologie",
            duration_minutes=30,
            weekdays=list(range(7)),
            effective_from=today - timedelta(days=5),
        )
        past_day = today - timedelta(days=2)
        future_day = today + timedelta(days=1)
        ensure_tasks_for_user(self.user, past_day, future_day)
        original_past_task = LearningTask.objects.get(
            owner=self.user,
            date=past_day,
            source_kind="study_plan",
            source_id=plan.pk,
        )
        original_past_task.done = True
        original_past_task.save(update_fields=["done"])

        plan.duration_minutes = 20
        plan.save()
        ensure_tasks_for_user(self.user, future_day, future_day)

        original_past_task.refresh_from_db()
        updated_future_task = LearningTask.objects.get(
            owner=self.user,
            date=future_day,
            source_kind="study_plan",
            source_id=plan.pk,
        )
        self.assertEqual(original_past_task.minutes, 30)
        self.assertTrue(original_past_task.done)
        self.assertEqual(updated_future_task.minutes, 20)

    def test_deleting_plan_keeps_past_tasks_and_removes_future_tasks(self):
        today = date.today()
        plan = StudyPlan.objects.create(
            owner=self.user,
            subject="Geschichte",
            duration_minutes=30,
            weekdays=list(range(7)),
            effective_from=today - timedelta(days=3),
        )
        past_day = today - timedelta(days=1)
        future_day = today + timedelta(days=1)
        plan_id = plan.pk
        ensure_tasks_for_user(self.user, past_day, future_day)

        plan.delete()

        self.assertTrue(
            LearningTask.objects.filter(
                owner=self.user,
                date=past_day,
                source_kind="study_plan",
                source_id=plan_id,
            ).exists()
        )
        self.assertFalse(
            LearningTask.objects.filter(
                owner=self.user,
                date=future_day,
                source_kind="study_plan",
                source_id=plan_id,
            ).exists()
        )

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
            effective_from=start_date,
            active=True,
            overrides_by_vacation=True,
        )
        vacation = Vacation.objects.create(
            name="Winter break",
            start_date=date(2026, 2, 2),
            end_date=date(2026, 2, 6),
        )
        vacation.users.add(self.user)

        ensure_tasks_for_user(self.user, start_date, end_date)

        self.assertFalse(
            LearningTask.objects.filter(
                owner=self.user,
                source_kind="study_plan",
                date=date(2026, 2, 2),
            ).exists()
        )

    def test_vacation_can_be_assigned_to_multiple_users(self):
        second_user = User.objects.create_user(username="bob")
        start_date = date(2026, 3, 2)
        end_date = date(2026, 3, 6)
        for user in [self.user, second_user]:
            StudyPlan.objects.create(
                owner=user,
                subject="Mathe",
                duration_minutes=30,
                weekdays=list(range(7)),
                effective_from=start_date,
                overrides_by_vacation=True,
            )
        vacation = Vacation.objects.create(
            name="Frühlingsferien",
            start_date=start_date,
            end_date=end_date,
        )
        vacation.users.add(self.user, second_user)

        for user in [self.user, second_user]:
            ensure_tasks_for_user(user, start_date, end_date)

        self.assertEqual(vacation.users.count(), 2)
        self.assertFalse(
            LearningTask.objects.filter(
                source_kind="study_plan",
                date=start_date,
            ).exists()
        )

    def test_assigning_vacation_removes_existing_future_plan_tasks(self):
        future_day = date.today() + timedelta(days=2)
        plan = StudyPlan.objects.create(
            owner=self.user,
            subject="Physik",
            duration_minutes=30,
            weekdays=list(range(7)),
            effective_from=date.today(),
            overrides_by_vacation=True,
        )
        ensure_tasks_for_user(self.user, future_day, future_day)
        self.assertTrue(
            LearningTask.objects.filter(
                owner=self.user,
                date=future_day,
                source_kind="study_plan",
                source_id=plan.pk,
            ).exists()
        )
        vacation = Vacation.objects.create(
            name="Freie Tage",
            start_date=future_day,
            end_date=future_day,
        )
        vacation.users.add(self.user)

        ensure_tasks_for_user(self.user, future_day, future_day)

        self.assertFalse(
            LearningTask.objects.filter(
                owner=self.user,
                date=future_day,
                source_kind="study_plan",
                source_id=plan.pk,
            ).exists()
        )

    def test_admin_can_assign_vacation_to_multiple_users_from_form(self):
        second_user = User.objects.create_user(username="bob")
        admin = User.objects.create_user(username="admin", is_superuser=True, is_staff=True)
        self.client.force_login(admin)

        response = self.client.post(
            "/vacations/new/",
            {
                "name": "Sommerferien",
                "start_date": "2026-07-01",
                "end_date": "2026-07-14",
                "users": [self.user.pk, second_user.pk],
            },
        )

        self.assertEqual(response.status_code, 302)
        vacation = Vacation.objects.get(name="Sommerferien")
        self.assertSetEqual(
            set(vacation.users.values_list("pk", flat=True)),
            {self.user.pk, second_user.pk},
        )

    def test_regular_user_cannot_assign_vacation_to_another_user(self):
        second_user = User.objects.create_user(username="bob")
        self.client.force_login(self.user)

        response = self.client.post(
            "/vacations/new/",
            {
                "name": "Private Ferien",
                "start_date": "2026-07-01",
                "end_date": "2026-07-14",
                "users": [second_user.pk],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Vacation.objects.filter(name="Private Ferien").exists())

    def test_calendar_can_show_a_past_month(self):
        self.client.force_login(self.user)

        response = self.client.get("/calendar/?month=2020-01")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Januar 2020")
