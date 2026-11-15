from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from typing import TypeVar

from app.profiles import SSHProfile
from ssh.sftp_client import AuthPromptCallback, SftpClient

T = TypeVar("T")
SftpOperation = Callable[[SftpClient], Awaitable[T]]


class SftpSession:
    """Keeps one authenticated SFTP connection alive for repeated UI actions."""

    def __init__(
        self,
        profile: SSHProfile,
        password: str | None,
        on_auth_prompt: AuthPromptCallback,
    ) -> None:
        self.profile = profile
        self.password = password
        self.on_auth_prompt = on_auth_prompt
        self.key = (
            profile.id,
            profile.host,
            profile.port,
            profile.username,
            profile.auth_type,
            password or "",
        )
        self._client: SftpClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._closed = False
        self._thread = threading.Thread(
            target=self._thread_main,
            name=f"sftp-session-{profile.name}",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait()

    def submit(self, operation: SftpOperation[T]) -> Future[T]:
        if self._closed:
            future: Future[T] = Future()
            future.set_exception(RuntimeError("SFTP session is closed."))
            return future
        assert self._loop is not None
        return asyncio.run_coroutine_threadsafe(self._run_operation(operation), self._loop)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        loop = self._loop
        if loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(self._close_client(), loop)
        try:
            future.result(timeout=5)
        except Exception:
            pass
        loop.call_soon_threadsafe(loop.stop)
        self._thread.join(timeout=2)

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            if self._client is not None:
                loop.run_until_complete(self._close_client())
            loop.close()

    async def _run_operation(self, operation: SftpOperation[T]) -> T:
        client = await self._ensure_client()
        try:
            return await operation(client)
        except Exception as exc:
            if self._is_connection_error(exc):
                await self._close_client()
            raise

    async def _ensure_client(self) -> SftpClient:
        if self._client is None:
            client = SftpClient(
                profile=self.profile,
                password=self.password,
                on_auth_prompt=self.on_auth_prompt,
            )
            await client.connect()
            self._client = client
        return self._client

    async def _close_client(self) -> None:
        if self._client is None:
            return
        client = self._client
        self._client = None
        await client.close()

    @staticmethod
    def _is_connection_error(exc: Exception) -> bool:
        try:
            import asyncssh
        except ImportError:
            return isinstance(exc, (ConnectionError, OSError, EOFError))
        return isinstance(
            exc,
            (
                asyncssh.ChannelOpenError,
                asyncssh.ConnectionLost,
                asyncssh.DisconnectError,
                asyncssh.ProcessError,
                ConnectionError,
                EOFError,
                OSError,
            ),
        )
