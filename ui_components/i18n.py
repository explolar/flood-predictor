"""
Feature 18: Multi-Language UI.
Simple translation system using JSON translation files.
"""

import json
import os

_TRANSLATIONS_DIR = os.path.join(os.path.dirname(__file__), 'translations')
_cache = {}


def _load_translations(lang):
    """Load translations for a language code."""
    if lang in _cache:
        return _cache[lang]

    path = os.path.join(_TRANSLATIONS_DIR, f'{lang}.json')
    if not os.path.exists(path):
        _cache[lang] = {}
        return {}

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    _cache[lang] = data
    return data


class Translator:
    """Multi-language translation for UI strings."""

    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'hi': 'हिन्दी (Hindi)',
        'bn': 'বাংলা (Bengali)',
        'ta': 'தமிழ் (Tamil)',
    }

    def __init__(self, lang='en'):
        self.lang = lang
        self.translations = _load_translations(lang)
        self.fallback = _load_translations('en') if lang != 'en' else {}

    def t(self, key, **kwargs):
        """
        Translate a key. Falls back to English, then the key itself.

        Supports format strings: t('hello', name='World') → "Hello, World!"
        """
        text = self.translations.get(key) or self.fallback.get(key) or key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text

    def set_language(self, lang):
        """Switch language."""
        self.lang = lang
        self.translations = _load_translations(lang)
        if lang != 'en':
            self.fallback = _load_translations('en')
