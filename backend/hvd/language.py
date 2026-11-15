"""User language preference stored as config entry ``language``.

Unknown / missing values resolve to English when consumed by the UI/backend helpers.
No write-time validation — users may store any string in config.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "ru")
LANGUAGE_CONFIG_KEY = "language"


def normalize_language(value: str | None) -> str:
    """Map a stored/system tag to a supported UI language; default English."""
    if value is None:
        return DEFAULT_LANGUAGE
    raw = str(value).strip().lower()
    if not raw:
        return DEFAULT_LANGUAGE
    if raw in ("en", "eng", "english") or raw.startswith("en-") or raw.startswith("en_"):
        return "en"
    if raw in ("ru", "rus", "russian") or raw.startswith("ru-") or raw.startswith("ru_"):
        return "ru"
    return DEFAULT_LANGUAGE


class LanguageAwareAuthBackend:
    """Proxy around SqlAuthBackend that exposes ``get_language`` from config."""

    def __init__(self, backend, config_store):
        self._backend = backend
        self._config_store = config_store

    def __getattr__(self, name: str):
        return getattr(self._backend, name)

    def get_language(self, username: str) -> str | None:
        """Raw config value, or None if the user has no ``language`` entry yet."""
        group_id = self._backend.get_user_group_id(username)
        if group_id is None:
            return None
        entry = self._config_store.get(LANGUAGE_CONFIG_KEY, group_read=group_id)
        if entry is None:
            return None
        value = entry.get("value")
        if value is None or not str(value).strip():
            return None
        return str(value).strip()
