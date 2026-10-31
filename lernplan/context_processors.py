from .models import UserPreference


def user_theme(request):
    theme = "standard"
    if request.user.is_authenticated:
        preference = UserPreference.objects.filter(user=request.user).first()
        if preference:
            theme = preference.theme
    return {
        "current_theme": theme,
        "theme_choices": UserPreference.THEME_CHOICES,
    }
