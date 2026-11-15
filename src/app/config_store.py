from __future__ import annotations

# Keep the legacy BidiSSH storage identifier so existing local profiles and
# OS-keychain passwords remain accessible after the public product rename.
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.profiles import ProfileCollection
from app.settings import AppSettings

T = TypeVar("T", bound=BaseModel)


def _config_root(app_name: str = "BidiSSH") -> Path:
    try:
        from platformdirs import user_config_dir
    except ImportError:  # pragma: no cover - dependency is declared.
        return Path.home() / f".{app_name.lower()}"
    return Path(user_config_dir(app_name, appauthor=False))


class ConfigStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _config_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.profiles_path = self.root / "profiles.json"
        self.settings_path = self.root / "settings.json"

    def load_profiles(self) -> ProfileCollection:
        return self._load_model(self.profiles_path, ProfileCollection)

    def save_profiles(self, profiles: ProfileCollection) -> None:
        self._save_model(self.profiles_path, profiles)

    def load_settings(self) -> AppSettings:
        return self._load_model(self.settings_path, AppSettings)

    def save_settings(self, settings: AppSettings) -> None:
        self._save_model(self.settings_path, settings)

    def _load_model(self, path: Path, model_type: type[T]) -> T:
        if not path.exists():
            return model_type()
        try:
            return model_type.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, json.JSONDecodeError) as exc:
            backup = path.with_suffix(path.suffix + ".invalid")
            path.replace(backup)
            raise RuntimeError(f"Invalid config moved to {backup}") from exc

    def _save_model(self, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            model.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )
        tmp_path.replace(path)
