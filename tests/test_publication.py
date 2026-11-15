from __future__ import annotations

import tomllib
from pathlib import Path

from app.config_store import ConfigStore
from app.keyring_store import KeyringStore


def test_window_branding_uses_isolated_settings(qtbot, monkeypatch, tmp_path) -> None:
    import app.main_window as window_module

    monkeypatch.setattr(window_module, "ConfigStore", lambda: ConfigStore(tmp_path))
    window = window_module.MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "Kav SSH Terminal"
    assert window.store.root == tmp_path


def test_rename_preserves_existing_config_and_keychain_namespace(monkeypatch, tmp_path) -> None:
    from app.config_store import _config_root

    seen = []

    def config_dir(appname, appauthor):
        seen.append(appname)
        return str(tmp_path / appname)

    monkeypatch.setattr("platformdirs.user_config_dir", config_dir)
    assert _config_root() == tmp_path / "BidiSSH"
    assert seen == ["BidiSSH"]
    # Constructing the adapter does not read or write the real keychain.
    assert KeyringStore().service_name == "BidiSSH"


def test_distribution_name_command_and_license() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "kav-ssh-terminal"
    assert project["scripts"]["kav-ssh"] == "main:main"
    assert project["license"] == "MIT"
    assert (root / "Start Kav SSH Terminal.cmd").is_file()
