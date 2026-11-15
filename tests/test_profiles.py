from __future__ import annotations

from app.config_store import ConfigStore
from app.profiles import AuthType, ProfileCollection, SSHProfile


def test_profile_config_never_contains_password(tmp_path) -> None:
    store = ConfigStore(tmp_path)
    profile = SSHProfile(
        name="Prod",
        host="example.com",
        username="root",
        auth_type=AuthType.PASSWORD,
        tags="prod, linux, prod",
    )
    collection = ProfileCollection()
    collection.upsert(profile)

    store.save_profiles(collection)
    raw = store.profiles_path.read_text(encoding="utf-8")

    assert "password" in raw
    assert "secret" not in raw
    assert "prod" in raw
    assert store.load_profiles().profiles[0].tags == ["linux", "prod"]


def test_profile_upsert_replaces_existing_profile() -> None:
    profile = SSHProfile(name="One", host="host", username="user")
    collection = ProfileCollection(profiles=[profile])

    collection.upsert(profile.model_copy(update={"name": "Two"}))

    assert len(collection.profiles) == 1
    assert collection.profiles[0].name == "Two"
