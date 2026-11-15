from __future__ import annotations

from app.keyring_store import MemorySecretStore
from app.profiles import SSHProfile


def test_memory_secret_store_behaves_like_keyring_wrapper() -> None:
    profile = SSHProfile(name="Local", host="localhost", username="seo")
    store = MemorySecretStore()

    store.set_password(profile, "secret")

    assert store.get_password(profile) == "secret"
    store.delete_password(profile)
    assert store.get_password(profile) is None
