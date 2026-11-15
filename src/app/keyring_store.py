from __future__ import annotations

# Keep the legacy BidiSSH storage identifier so existing local profiles and
# OS-keychain passwords remain accessible after the public product rename.
from dataclasses import dataclass, field

from app.profiles import SSHProfile


class KeyringUnavailable(RuntimeError):
    pass


class KeyringStore:
    def __init__(self, service_name: str = "BidiSSH") -> None:
        self.service_name = service_name

    def set_password(self, profile: SSHProfile, password: str) -> None:
        keyring = self._keyring()
        keyring.set_password(self.service_name, profile.keyring_username, password)

    def get_password(self, profile: SSHProfile) -> str | None:
        keyring = self._keyring()
        return keyring.get_password(self.service_name, profile.keyring_username)

    def delete_password(self, profile: SSHProfile) -> None:
        keyring = self._keyring()
        try:
            keyring.delete_password(self.service_name, profile.keyring_username)
        except keyring.errors.PasswordDeleteError:
            return

    @staticmethod
    def _keyring():
        try:
            import keyring
        except ImportError as exc:  # pragma: no cover - dependency is declared.
            raise KeyringUnavailable("The keyring package is not installed.") from exc

        backend = keyring.get_keyring()
        if backend is None:
            raise KeyringUnavailable("No OS keyring backend is available.")
        return keyring


@dataclass
class MemorySecretStore:
    """Test-only keyring-compatible store."""

    values: dict[tuple[str, str], str] = field(default_factory=dict)
    service_name: str = "BidiSSH"

    def set_password(self, profile: SSHProfile, password: str) -> None:
        self.values[(self.service_name, profile.keyring_username)] = password

    def get_password(self, profile: SSHProfile) -> str | None:
        return self.values.get((self.service_name, profile.keyring_username))

    def delete_password(self, profile: SSHProfile) -> None:
        self.values.pop((self.service_name, profile.keyring_username), None)
