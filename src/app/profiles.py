from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthType(StrEnum):
    PASSWORD = "password"
    INTERACTIVE = "interactive"
    PRIVATE_KEY = "private_key"
    AGENT = "agent"


class SSHProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: Annotated[str, Field(min_length=1, max_length=80)]
    host: Annotated[str, Field(min_length=1, max_length=255)]
    port: Annotated[int, Field(ge=1, le=65535)] = 22
    username: Annotated[str, Field(min_length=1, max_length=128)]
    auth_type: AuthType = AuthType.PASSWORD
    private_key_path: str | None = None
    default_remote_path: str = "~"
    group: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("private_key_path")
    @classmethod
    def normalize_private_key_path(cls, value: str | None) -> str | None:
        if not value:
            return None
        return str(Path(value).expanduser())

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        return sorted({part for part in value if part})

    @property
    def keyring_username(self) -> str:
        return f"{self.username}@{self.host}:{self.port}"


class ProfileCollection(BaseModel):
    profiles: list[SSHProfile] = Field(default_factory=list)

    def upsert(self, profile: SSHProfile) -> None:
        for index, existing in enumerate(self.profiles):
            same_profile = (
                existing.name == profile.name
                and existing.host == profile.host
                and existing.port == profile.port
                and existing.username == profile.username
            )
            if existing.id == profile.id or same_profile:
                if same_profile:
                    profile = profile.model_copy(update={"id": existing.id})
                self.profiles[index] = profile
                return
        self.profiles.append(profile)
        self.profiles.sort(key=lambda item: (item.group or "", item.name.lower()))

    def by_id(self, profile_id: str) -> SSHProfile | None:
        return next((profile for profile in self.profiles if profile.id == profile_id), None)

    def remove(self, profile_id: str) -> SSHProfile | None:
        for index, profile in enumerate(self.profiles):
            if profile.id == profile_id:
                return self.profiles.pop(index)
        return None
