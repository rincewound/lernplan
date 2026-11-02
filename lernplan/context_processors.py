from .models import UserPreference
from .motivation import choose_motivations

BITMAP_SKINS = {
    "forest": "skins/forest.css",
    "lotr": "skins/lotr.css",
    "botw": "skins/botw.css",
}


def user_theme(request):
    theme = "standard"
    if request.user.is_authenticated:
        preference = UserPreference.objects.filter(user=request.user).first()
        if preference:
            theme = preference.theme
    return {
        "current_theme": theme,
        "theme_choices": UserPreference.THEME_CHOICES,
        "skin_stylesheet": BITMAP_SKINS.get(theme),
        "motivation": choose_motivations(request) if request.user.is_authenticated else None,
    }
