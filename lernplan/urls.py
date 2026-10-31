from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("my/", views.dashboard, name="my"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("day/<str:target_date>/", views.day_detail, name="day_detail"),
    path("plans/", views.study_plans, name="study_plans"),
    path("plans/new/", views.create_study_plan, name="create_study_plan"),
    path("plans/<int:pk>/edit/", views.edit_study_plan, name="edit_study_plan"),
    path("plans/<int:pk>/delete/", views.delete_study_plan, name="delete_study_plan"),
    path("exams/new/", views.create_exam, name="create_exam"),
    path("exams/<int:pk>/edit/", views.edit_exam, name="edit_exam"),
    path("vacations/new/", views.create_vacation, name="create_vacation"),
    path("tasks/<int:pk>/toggle/", views.toggle_task, name="toggle_task"),
]
