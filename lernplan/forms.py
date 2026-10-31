from django import forms
from django.contrib.auth import get_user_model

from .models import Exam, StudyPlan, Vacation

User = get_user_model()

DAY_CHOICES = [
    (0, "Montag"),
    (1, "Dienstag"),
    (2, "Mittwoch"),
    (3, "Donnerstag"),
    (4, "Freitag"),
    (5, "Samstag"),
    (6, "Sonntag"),
]


class StudyPlanForm(forms.ModelForm):
    owner = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Besitzer",
    )
    weekdays = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Wochentage",
    )

    class Meta:
        model = StudyPlan
        fields = [
            "owner",
            "subject",
            "duration_minutes",
            "weekdays",
            "effective_from",
            "effective_until",
            "active",
            "overrides_by_vacation",
        ]
        labels = {
            "subject": "Fach",
            "duration_minutes": "Lernzeit in Minuten",
            "effective_from": "Gültig ab",
            "effective_until": "Gültig bis (optional)",
            "active": "Aktiv",
            "overrides_by_vacation": "Durch Ferien überschreiben",
        }
        widgets = {
            "effective_from": forms.DateInput(attrs={"type": "date"}),
            "effective_until": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        visible_users = kwargs.pop("visible_users", [])
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.filter(
            pk__in=[user.pk for user in visible_users or [self.user]]
        ).order_by("username")
        if self.instance.pk:
            self.fields["weekdays"].initial = list(self.instance.weekdays)
            self.fields["owner"].initial = self.instance.owner
        elif self.user:
            self.fields["owner"].initial = self.user

    def clean_weekdays(self):
        value = self.cleaned_data.get("weekdays", [])
        return [int(day) for day in value]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.owner = self.cleaned_data.get("owner") or self.user or instance.owner
        instance.weekdays = self.cleaned_data.get("weekdays", [])
        if commit:
            instance.save()
        return instance


class ExamForm(forms.ModelForm):
    owner = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Besitzer",
    )

    class Meta:
        model = Exam
        fields = [
            "owner",
            "title",
            "subject",
            "exam_date",
            "duration_minutes",
            "days_before_exam",
            "content",
        ]
        labels = {
            "title": "Titel",
            "subject": "Fach",
            "exam_date": "Prüfungsdatum",
            "duration_minutes": "Lernzeit in Minuten",
            "days_before_exam": "Tage vor der Prüfung",
            "content": "Inhalte / Freitext",
        }
        widgets = {
            "exam_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        visible_users = kwargs.pop("visible_users", [])
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.filter(
            pk__in=[user.pk for user in visible_users or [self.user]]
        ).order_by("username")
        if self.instance.pk:
            self.fields["owner"].initial = self.instance.owner
        elif self.user:
            self.fields["owner"].initial = self.user

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.owner = self.cleaned_data.get("owner") or self.user or instance.owner
        if commit:
            instance.save()
        return instance


class VacationForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Gilt für Benutzer",
    )

    class Meta:
        model = Vacation
        fields = ["name", "start_date", "end_date", "users"]
        labels = {
            "name": "Name",
            "start_date": "Startdatum",
            "end_date": "Enddatum",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        visible_users = kwargs.pop("visible_users", [])
        super().__init__(*args, **kwargs)
        users = visible_users or ([self.user] if self.user else [])
        user_ids = [user.pk for user in users]
        self.fields["users"].queryset = User.objects.filter(
            pk__in=user_ids
        ).order_by("username")
        if not self.instance.pk and len(user_ids) == 1:
            self.fields["users"].initial = user_ids

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("Das Enddatum muss nach dem Startdatum liegen.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.created_by = self.user
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class UserSelectForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Benutzer")

    def __init__(self, *args, **kwargs):
        visible_users = kwargs.pop("visible_users", [])
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(
            pk__in=[user.pk for user in visible_users]
        ).order_by("username")
