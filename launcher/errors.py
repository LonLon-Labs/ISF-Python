class LauncherError(Exception):
    """A failure the user should see, with a plain-language title and an optional hint."""

    def __init__(self, title, detail="", hint=""):
        super().__init__(title)
        self.title = title
        self.detail = detail
        self.hint = hint

    def full_text(self):
        parts = [self.title]
        if self.hint:
            parts.append(self.hint)
        if self.detail:
            parts.append("Details:\n" + self.detail)
        return "\n\n".join(parts)


class NeedDisc(Exception):
    """Setup cannot continue without the user's disc image."""


class Cancelled(Exception):
    """The user pressed Cancel."""
