from .models import UserPreference
from .motivation import choose_motivations
from .themes import DEFAULT_THEME, THEME_CHOICES, THEMES


def user_theme(request):
    key = DEFAULT_THEME
    if request.user.is_authenticated:
        preference = UserPreference.objects.filter(user=request.user).first()
        if preference and preference.theme in THEMES:
            key = preference.theme
    theme = THEMES[key]
    return {
        "current_theme": key,
        "theme_choices": THEME_CHOICES,
        "theme_stylesheets": theme.stylesheets,
        "theme_is_bitmap": theme.is_bitmap,
        "motivation": choose_motivations(request) if request.user.is_authenticated else None,
    }
