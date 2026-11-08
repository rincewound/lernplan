"""Single source of truth for the selectable themes.

Adding a theme: add an entry here, put its stylesheet in static/skins/ and run
makemigrations (the labels end up in UserPreference.theme.choices).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    label: str
    stylesheets: tuple[str, ...] = ()
    # Bitmap skins get data-skin="bitmap" and build on skins/bitmap.css.
    is_bitmap: bool = False


DEFAULT_THEME = "standard"

THEMES = {
    "standard": Theme("Standard"),
    "space": Theme("Space", ("skins/space.css",)),
    "unicorn": Theme("Einhorn", ("skins/unicorn.css",)),
    "forest": Theme("Wald", ("skins/bitmap.css", "skins/forest.css"), is_bitmap=True),
    "lotr": Theme(
        "Drachenfeuer",
        ("skins/bitmap.css", "skins/storybook.css", "skins/lotr.css"),
        is_bitmap=True,
    ),
    "botw": Theme(
        "Wildnis",
        ("skins/bitmap.css", "skins/storybook.css", "skins/botw.css"),
        is_bitmap=True,
    ),
}

THEME_CHOICES = [(key, theme.label) for key, theme in THEMES.items()]
