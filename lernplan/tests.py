from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import TestCase

from .models import Exam, LearningTask, StudyPlan, UserPreference, Vacation, ensure_tasks_for_user
from .motivation import SENTENCES
from .themes import THEME_CHOICES, THEMES

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

    def test_exam_edit_form_prefills_exam_date(self):
        exam = Exam.objects.create(
            owner=self.user,
            title="Klausur",
            subject="Mathe",
            exam_date=date(2026, 11, 12),
        )
        self.client.force_login(self.user)

        response = self.client.get(f"/exams/{exam.pk}/edit/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-11-12"')

    def test_exam_list_shows_future_exams_and_effort(self):
        today = date.today()
        Exam.objects.create(
            owner=self.user,
            title="Kommende Klausur",
            subject="Mathe",
            exam_date=today + timedelta(days=4),
            days_before_exam=5,
            duration_minutes=45,
        )
        Exam.objects.create(
            owner=self.user,
            title="Vergangene Klausur",
            subject="Deutsch",
            exam_date=today - timedelta(days=1),
        )
        self.client.force_login(self.user)

        response = self.client.get("/exams/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kommende Klausur")
        self.assertContains(response, "5 Tage x 45 Minuten")
        self.assertNotContains(response, "Vergangene Klausur")

    def test_deleting_exam_removes_its_tasks(self):
        exam = Exam.objects.create(
            owner=self.user,
            title="Klausur",
            subject="Mathe",
            exam_date=date.today() + timedelta(days=2),
        )
        task = LearningTask.objects.create(
            owner=self.user,
            subject=exam.subject,
            title="Klausur preparation",
            date=date.today() + timedelta(days=1),
            source_kind="exam",
            source_id=exam.pk,
        )
        self.client.force_login(self.user)

        response = self.client.post(f"/exams/{exam.pk}/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Exam.objects.filter(pk=exam.pk).exists())
        self.assertFalse(LearningTask.objects.filter(pk=task.pk).exists())

    def test_logout_uses_post_and_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post("/logout/")

        self.assertRedirects(response, "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_can_choose_and_persist_theme(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/theme/",
            {"theme": "space", "next": "/calendar/"},
        )

        self.assertRedirects(response, "/calendar/")
        self.assertEqual(UserPreference.objects.get(user=self.user).theme, "space")
        themed_page = self.client.get("/calendar/")
        self.assertContains(themed_page, '<body data-theme="space">')
        self.assertContains(themed_page, 'class="nav-link"')

    def test_theme_selection_rejects_invalid_values_and_external_redirects(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/theme/",
            {"theme": "unknown", "next": "https://example.com/"},
        )

        self.assertRedirects(response, "/my/")
        self.assertFalse(UserPreference.objects.filter(user=self.user).exists())

    def test_forest_bitmap_skin_persists_and_renders_across_pages(self):
        self.client.force_login(self.user)

        response = self.client.post("/theme/", {"theme": "forest", "next": "/my/"}, follow=True)

        self.assertContains(response, "Theme gespeichert.")
        self.assertEqual(UserPreference.objects.get(user=self.user).theme, "forest")
        for path in (
            "/my/",
            "/calendar/",
            f"/day/{date.today().isoformat()}/",
            "/plans/",
            "/plans/new/",
            "/exams/",
            "/exams/new/",
            "/vacations/",
            "/vacations/new/",
        ):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertContains(page, 'data-theme="forest" data-skin="bitmap"')
                self.assertContains(page, "/static/skins/bitmap.css")
                self.assertContains(page, "/static/skins/forest.css")

    def test_switching_from_bitmap_skin_does_not_affect_other_themes(self):
        self.client.force_login(self.user)
        UserPreference.objects.create(user=self.user, theme="forest")

        for theme in ("standard", "space", "unicorn"):
            with self.subTest(theme=theme):
                page = self.client.post("/theme/", {"theme": theme, "next": "/my/"}, follow=True)
                self.assertContains(page, f'<body data-theme="{theme}">')
                self.assertNotContains(page, "skins/bitmap.css")
                self.assertNotContains(page, "skins/forest.css")

    def test_every_theme_stylesheet_exists_and_is_loaded(self):
        self.client.force_login(self.user)
        self.assertEqual(UserPreference.THEME_CHOICES, THEME_CHOICES)

        for key, theme in THEMES.items():
            with self.subTest(theme=key):
                UserPreference.objects.update_or_create(user=self.user, defaults={"theme": key})
                page = self.client.get("/my/")
                for stylesheet in theme.stylesheets:
                    self.assertIsNotNone(finders.find(stylesheet))
                    self.assertContains(page, f"/static/{stylesheet}")
                skin_attribute = ' data-skin="bitmap"' if theme.is_bitmap else ""
                self.assertContains(page, f'<body data-theme="{key}"{skin_attribute}>')

    def test_unicorn_theme_uses_its_own_skin_and_emblem(self):
        self.client.force_login(self.user)

        page = self.client.post("/theme/", {"theme": "unicorn", "next": "/my/"}, follow=True)

        self.assertContains(page, "/static/skins/unicorn.css")
        self.assertIsNotNone(finders.find("skins/unicorn/emblem.png"))

    def test_stale_stored_theme_falls_back_to_default(self):
        self.client.force_login(self.user)
        UserPreference.objects.create(user=self.user, theme="retired")

        page = self.client.get("/my/")

        self.assertContains(page, '<body data-theme="standard">')

    def test_themes_are_isolated_per_user(self):
        second_user = User.objects.create_user(username="bob")
        UserPreference.objects.create(user=self.user, theme="forest")
        self.client.force_login(second_user)

        response = self.client.get("/my/")

        self.assertContains(response, '<body data-theme="standard">')

    def test_lotr_theme_persists_and_loads_its_own_artwork(self):
        self.client.force_login(self.user)

        page = self.client.post("/theme/", {"theme": "lotr", "next": "/my/"}, follow=True)

        self.assertEqual(UserPreference.objects.get(user=self.user).theme, "lotr")
        self.assertContains(page, 'data-theme="lotr" data-skin="bitmap"')
        self.assertContains(page, "/static/skins/lotr.css")
        self.assertNotContains(page, "/static/skins/forest.css")
        self.assertContains(page, '<option value="lotr" selected>')
        self.assertContains(page, "Theme gespeichert.")

    def test_botw_theme_persists_and_loads_only_its_own_artwork(self):
        self.client.force_login(self.user)

        page = self.client.post("/theme/", {"theme": "botw", "next": "/my/"}, follow=True)

        self.assertEqual(UserPreference.objects.get(user=self.user).theme, "botw")
        self.assertContains(page, 'data-theme="botw" data-skin="bitmap"')
        self.assertContains(page, "/static/skins/bitmap.css")
        self.assertContains(page, "/static/skins/botw.css")
        self.assertNotContains(page, "/static/skins/lotr.css")
        self.assertNotContains(page, "/static/skins/forest.css")
        self.assertContains(page, '<option value="botw" selected>')
        self.assertContains(page, "Theme gespeichert.")

    def test_motivations_change_on_reload_for_every_theme(self):
        self.client.force_login(self.user)
        self.assertEqual(len(set(SENTENCES)), 50)

        previous = set()
        for theme, _label in UserPreference.THEME_CHOICES:
            UserPreference.objects.update_or_create(user=self.user, defaults={"theme": theme})
            for _reload in range(3):
                page = self.client.get("/my/")
                motivations = page.context["motivation"]
                current = set(motivations.values())
                self.assertEqual(len(current), 3)
                self.assertTrue(current.issubset(SENTENCES))
                self.assertTrue(current.isdisjoint(previous))
                for sentence in current:
                    self.assertContains(page, sentence, count=1)
                previous = current

    def test_motivations_rotate_on_other_pages_and_skip_anonymous_login(self):
        login_page = self.client.get("/login/")
        self.assertNotContains(login_page, 'class="motivation')
        self.assertNotIn("motivation_indices", self.client.session)
        self.client.force_login(self.user)
        dashboard = self.client.get("/my/")

        calendar = self.client.get("/calendar/")

        self.assertContains(calendar, calendar.context["motivation"]["top"])
        self.assertNotEqual(
            dashboard.context["motivation"]["top"], calendar.context["motivation"]["top"]
        )
        self.assertNotContains(calendar, calendar.context["motivation"]["open"])

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
        self.assertEqual(tasks.first().title, "French")

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

    def test_vacation_crud_allows_admin_to_list_edit_and_delete(self):
        second_user = User.objects.create_user(username="bob")
        admin = User.objects.create_user(username="admin", is_superuser=True, is_staff=True)
        vacation = Vacation.objects.create(
            name="Sommerferien",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 14),
            created_by=admin,
        )
        vacation.users.add(self.user, second_user)
        self.client.force_login(admin)

        list_response = self.client.get("/vacations/")
        edit_form_response = self.client.get(f"/vacations/{vacation.pk}/edit/")
        edit_response = self.client.post(
            f"/vacations/{vacation.pk}/edit/",
            {
                "name": "Lange Sommerferien",
                "start_date": "2026-07-01",
                "end_date": "2026-07-20",
                "users": [self.user.pk],
            },
        )
        vacation.refresh_from_db()
        edited_users = set(vacation.users.values_list("pk", flat=True))
        delete_response = self.client.post(f"/vacations/{vacation.pk}/delete/")

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Sommerferien")
        self.assertContains(edit_form_response, 'value="2026-07-01"')
        self.assertContains(edit_form_response, 'value="2026-07-14"')
        self.assertRedirects(edit_response, "/vacations/")
        self.assertEqual(vacation.name, "Lange Sommerferien")
        self.assertSetEqual(edited_users, {self.user.pk})
        self.assertRedirects(delete_response, "/vacations/")
        self.assertFalse(Vacation.objects.filter(pk=vacation.pk).exists())

    def test_regular_user_can_manage_only_their_own_vacation(self):
        own_vacation = Vacation.objects.create(
            name="Eigene Ferien",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
            created_by=self.user,
        )
        own_vacation.users.add(self.user)
        shared_vacation = Vacation.objects.create(
            name="Gemeinsame Ferien",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 10),
        )
        shared_vacation.users.add(self.user, User.objects.create_user(username="bob"))
        self.client.force_login(self.user)

        list_response = self.client.get("/vacations/")
        own_edit_response = self.client.get(f"/vacations/{own_vacation.pk}/edit/")
        shared_edit_response = self.client.get(f"/vacations/{shared_vacation.pk}/edit/")
        shared_delete_response = self.client.post(
            f"/vacations/{shared_vacation.pk}/delete/"
        )

        self.assertContains(list_response, "Eigene Ferien")
        self.assertContains(list_response, "Gemeinsame Ferien")
        self.assertEqual(own_edit_response.status_code, 200)
        self.assertRedirects(shared_edit_response, "/vacations/")
        self.assertRedirects(shared_delete_response, "/vacations/")
        self.assertTrue(Vacation.objects.filter(pk=shared_vacation.pk).exists())

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
