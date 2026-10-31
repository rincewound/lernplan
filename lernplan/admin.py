from django.contrib import admin

from .models import Exam, LearningTask, StudyPlan, Vacation


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "subject",
        "duration_minutes",
        "effective_from",
        "effective_until",
        "active",
    )
    list_filter = ("active", "owner")

    def delete_queryset(self, request, queryset):
        for plan in queryset:
            plan.delete()


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("owner", "subject", "title", "exam_date")
    list_filter = ("owner", "exam_date")


@admin.register(Vacation)
class VacationAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "created_by")
    list_filter = ("start_date", "end_date", "users")


@admin.register(LearningTask)
class LearningTaskAdmin(admin.ModelAdmin):
    list_display = ("owner", "subject", "date", "done", "source_kind")
    list_filter = ("owner", "done", "source_kind")
