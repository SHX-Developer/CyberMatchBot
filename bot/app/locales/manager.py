import json
from pathlib import Path


class LocalizationManager:
    def __init__(self, locales_dir: Path, default_locale: str = 'ru') -> None:
        self.default_locale = default_locale
        self._translations: dict[str, dict[str, str]] = {}

        for file_path in locales_dir.glob('*.json'):
            locale_code = file_path.stem
            with file_path.open('r', encoding='utf-8') as f:
                self._translations[locale_code] = json.load(f)

        if self.default_locale not in self._translations:
            raise ValueError(f'Default locale {self.default_locale} is not present in locales')

    @property
    def supported_locales(self) -> tuple[str, ...]:
        return tuple(sorted(self._translations.keys()))

    def t(self, locale: str | None, key: str, **kwargs: object) -> str:
        selected_locale = locale if locale in self._translations else self.default_locale
        text = self._translations.get(selected_locale, {}).get(key)

        if text is None:
            text = self._translations[self.default_locale].get(key, key)

        if kwargs:
            return text.format(**kwargs)
        return text

    def texts_for_key(self, key: str) -> set[str]:
        return {
            payload[key]
            for payload in self._translations.values()
            if key in payload
        }

    def match_key(self, key: str, text: str | None) -> bool:
        if text is None:
            return False
        return text in self.texts_for_key(key)
