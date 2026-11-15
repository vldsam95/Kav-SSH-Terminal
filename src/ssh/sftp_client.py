from __future__ import annotations

import stat
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from shlex import quote

from app.profiles import AuthType, SSHProfile
from ssh.known_hosts import asyncssh_known_hosts_argument
from ssh.ssh_client import AuthPrompt

AuthPromptCallback = Callable[[AuthPrompt], str | None]


@dataclass(frozen=True)
class RemoteFile:
    name: str
    path: str
    size: int
    is_dir: bool
    permissions: int | None = None


class SftpClient:
    def __init__(
        self,
        profile: SSHProfile,
        password: str | None = None,
        key_passphrase: str | None = None,
        strict_known_hosts: bool = True,
        on_auth_prompt: AuthPromptCallback | None = None,
    ) -> None:
        self.profile = profile
        self.password = password
        self.key_passphrase = key_passphrase
        self.strict_known_hosts = strict_known_hosts
        self.on_auth_prompt = on_auth_prompt or (lambda _prompt: None)
        self._connection = None
        self._sftp = None

    async def connect(self) -> None:
        import asyncssh

        kwargs: dict[str, object] = {
            "host": self.profile.host,
            "port": self.profile.port,
            "username": self.profile.username,
            "known_hosts": asyncssh_known_hosts_argument(self.strict_known_hosts),
        }
        if self.profile.auth_type == AuthType.PASSWORD:
            kwargs["password"] = self.password
        elif self.profile.auth_type == AuthType.INTERACTIVE:
            kwargs["client_factory"] = self._interactive_client_factory
            kwargs["kbdint_auth"] = True
            kwargs["password_auth"] = True
        elif self.profile.auth_type == AuthType.PRIVATE_KEY and self.profile.private_key_path:
            kwargs["client_keys"] = [self.profile.private_key_path]
            if self.key_passphrase:
                kwargs["passphrase"] = self.key_passphrase
        elif self.profile.auth_type == AuthType.AGENT:
            kwargs["agent_path"] = None

        self._connection = await asyncssh.connect(**kwargs)
        self._sftp = await self._connection.start_sftp_client()

    async def close(self) -> None:
        if self._sftp is not None:
            self._sftp.exit()
        if self._connection is not None:
            self._connection.close()
            await self._connection.wait_closed()

    async def listdir(self, path: str) -> list[RemoteFile]:
        sftp = self._require_sftp()
        files: list[RemoteFile] = []
        async for entry in sftp.scandir(path):
            if entry.filename == ".":
                continue
            attrs = entry.attrs
            permissions = attrs.permissions
            base_path = "" if path in ("", ".") else path.rstrip("/")
            remote_path = entry.filename if not base_path else f"{base_path}/{entry.filename}"
            files.append(
                RemoteFile(
                    name=entry.filename,
                    path=remote_path,
                    size=attrs.size or 0,
                    is_dir=stat.S_ISDIR(permissions or 0),
                    permissions=permissions,
                )
            )
        return sorted(files, key=lambda file: (not file.is_dir, file.name.casefold()))

    async def upload(self, local_path: str | Path, remote_path: str) -> None:
        await self._require_sftp().put(str(local_path), remote_path)

    async def download(self, remote_path: str, local_path: str | Path) -> None:
        await self._require_sftp().get(remote_path, str(local_path))

    async def read_file(self, remote_path: str, max_bytes: int | None = None) -> bytes:
        sftp = self._require_sftp()
        if max_bytes is not None:
            attrs = await sftp.stat(remote_path)
            size = attrs.size or 0
            if size > max_bytes:
                raise RuntimeError(f"File is too large to edit in-app ({size:,} bytes).")

        temp_path = self._temp_path()
        try:
            await self.download(remote_path, temp_path)
            return Path(temp_path).read_bytes()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def write_file(self, remote_path: str, data: bytes) -> None:
        temp_path = self._temp_path()
        try:
            Path(temp_path).write_bytes(data)
            await self.upload(temp_path, remote_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def delete(self, remote_path: str) -> None:
        await self._require_sftp().remove(remote_path)

    async def delete_path(self, remote_path: str, is_dir: bool) -> None:
        if is_dir:
            await self._remove_tree(remote_path)
            return
        await self.delete(remote_path)

    async def rename(self, old_path: str, new_path: str) -> None:
        await self._require_sftp().rename(old_path, new_path)

    async def mkdir(self, remote_path: str) -> None:
        await self._require_sftp().mkdir(remote_path)

    async def chmod(self, remote_path: str, mode: int) -> None:
        await self._require_sftp().chmod(remote_path, mode)

    async def compress_directory_zip(self, remote_path: str, archive_path: str) -> None:
        connection = self._require_connection()
        remote = PurePosixPath(remote_path)
        archive = PurePosixPath(archive_path)
        parent = remote.parent.as_posix() or "."
        archive_parent = archive.parent.as_posix() or "."

        if archive_parent == parent:
            command = (
                f"cd {quote(parent)} && "
                f"zip -r -q -- {quote(archive.name)} {quote(remote.name)}"
            )
        else:
            command = f"zip -r -q -- {quote(archive_path)} {quote(remote_path)}"

        result = await connection.run(command, check=False)
        if result.exit_status == 0:
            return
        message = (result.stderr or result.stdout or "").strip()
        if not message:
            message = f"zip exited with status {result.exit_status}"
        raise RuntimeError(message)

    def _require_sftp(self):
        if self._sftp is None:
            raise RuntimeError("SFTP client is not connected.")
        return self._sftp

    def _require_connection(self):
        if self._connection is None:
            raise RuntimeError("SSH connection is not connected.")
        return self._connection

    def _interactive_client_factory(self):
        import asyncssh

        client = self

        class InteractiveAuthClient(asyncssh.SSHClient):
            def password_auth_requested(self):
                return client._ask_auth_prompt(
                    AuthPrompt(
                        title="SFTP password",
                        prompt="Password:",
                        echo=False,
                        default_response=client.password or "",
                    )
                )

            def kbdint_auth_requested(self):
                return ""

            def kbdint_challenge_received(self, name, instructions, lang, prompts):
                if not prompts:
                    return []

                responses: list[str] = []
                for prompt, echo in prompts:
                    response = client._ask_auth_prompt(
                        AuthPrompt(
                            title=name or "SFTP authentication",
                            prompt=prompt,
                            instructions=instructions,
                            echo=echo,
                            default_response=client._default_response_for_prompt(prompt),
                        )
                    )
                    if response is None:
                        return None
                    responses.append(response)
                return responses

        return InteractiveAuthClient()

    def _ask_auth_prompt(self, prompt: AuthPrompt) -> str | None:
        return self.on_auth_prompt(prompt)

    def _default_response_for_prompt(self, prompt: str) -> str:
        normalized = prompt.casefold()
        if "password" in normalized and self.password:
            return self.password
        return ""

    async def _remove_tree(self, remote_path: str) -> None:
        sftp = self._require_sftp()
        async for entry in sftp.scandir(remote_path):
            if entry.filename in (".", ".."):
                continue
            child_path = self._remote_child_path(remote_path, entry.filename)
            permissions = entry.attrs.permissions or 0
            if stat.S_ISDIR(permissions):
                await self._remove_tree(child_path)
            else:
                await sftp.remove(child_path)
        await sftp.rmdir(remote_path)

    @staticmethod
    def _remote_child_path(parent: str, child_name: str) -> str:
        if parent in ("", "."):
            return f"./{child_name}"
        return f"{parent.rstrip('/')}/{child_name}"

    @staticmethod
    def _temp_path() -> str:
        handle = tempfile.NamedTemporaryFile(prefix="bidi-sftp-", delete=False)
        try:
            return handle.name
        finally:
            handle.close()
