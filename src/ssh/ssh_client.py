from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass

from app.profiles import AuthType, SSHProfile
from ssh.known_hosts import asyncssh_known_hosts_argument

DataCallback = Callable[[str], None]
StatusCallback = Callable[[str], None]
ErrorCallback = Callable[[Exception], None]
AuthPromptCallback = Callable[["AuthPrompt"], str | None]


@dataclass(frozen=True)
class AuthPrompt:
    title: str
    prompt: str
    instructions: str = ""
    echo: bool = False
    default_response: str = ""


@dataclass(frozen=True)
class SSHConnectionOptions:
    profile: SSHProfile
    password: str | None = None
    key_passphrase: str | None = None
    columns: int = 100
    rows: int = 30
    strict_known_hosts: bool = True


class SshSessionRunner:
    """Runs one interactive SSH shell in a background asyncio loop."""

    def __init__(
        self,
        options: SSHConnectionOptions,
        on_data: DataCallback,
        on_status: StatusCallback | None = None,
        on_error: ErrorCallback | None = None,
        on_auth_prompt: AuthPromptCallback | None = None,
    ) -> None:
        self.options = options
        self.on_data = on_data
        self.on_status = on_status or (lambda _status: None)
        self.on_error = on_error or (lambda _exc: None)
        self.on_auth_prompt = on_auth_prompt or (lambda _prompt: None)
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._input_queue: asyncio.Queue[str | None] | None = None
        self._resize_queue: asyncio.Queue[tuple[int, int] | None] | None = None
        self._pending_size = (options.columns, options.rows)
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, name="ssh-session", daemon=True)
        self._thread.start()

    def send(self, data: str) -> None:
        if self._loop and self._input_queue:
            self._loop.call_soon_threadsafe(self._input_queue.put_nowait, data)

    def resize(self, columns: int, rows: int) -> None:
        self._pending_size = (max(1, columns), max(1, rows))
        if self._loop and self._resize_queue:
            self._loop.call_soon_threadsafe(self._resize_queue.put_nowait, self._pending_size)

    def stop(self) -> None:
        self._stop_event.set()
        if self._loop and self._input_queue:
            self._loop.call_soon_threadsafe(self._input_queue.put_nowait, None)
        if self._loop and self._resize_queue:
            self._loop.call_soon_threadsafe(self._resize_queue.put_nowait, None)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:  # pragma: no cover - integration path.
            self.on_error(exc)

    async def _run(self) -> None:
        import asyncssh

        self._loop = asyncio.get_running_loop()
        self._input_queue = asyncio.Queue()
        self._resize_queue = asyncio.Queue()
        profile = self.options.profile
        self.on_status(f"Connecting to {profile.host}:{profile.port}...")

        connect_kwargs: dict[str, object] = {
            "host": profile.host,
            "port": profile.port,
            "username": profile.username,
            "known_hosts": asyncssh_known_hosts_argument(self.options.strict_known_hosts),
        }
        if profile.auth_type == AuthType.PASSWORD:
            connect_kwargs["password"] = self.options.password
        elif profile.auth_type == AuthType.INTERACTIVE:
            connect_kwargs["client_factory"] = self._interactive_client_factory
            connect_kwargs["kbdint_auth"] = True
            connect_kwargs["password_auth"] = True
        elif profile.auth_type == AuthType.PRIVATE_KEY and profile.private_key_path:
            connect_kwargs["client_keys"] = [profile.private_key_path]
            if self.options.key_passphrase:
                connect_kwargs["passphrase"] = self.options.key_passphrase
        elif profile.auth_type == AuthType.AGENT:
            connect_kwargs["agent_path"] = None

        async with asyncssh.connect(**connect_kwargs) as connection:
            columns, rows = self._pending_size
            process = await connection.create_process(
                term_type="xterm-256color",
                term_size=(columns, rows),
                encoding="utf-8",
            )
            self.on_status(f"Connected to {profile.name}")
            await asyncio.gather(
                self._read_stream(process.stdout),
                self._read_stream(process.stderr),
                self._write_loop(process),
                self._resize_loop(process),
            )

    async def _read_stream(self, stream) -> None:
        while not self._stop_event.is_set():
            data = await stream.read(4096)
            if not data:
                return
            if data:
                self.on_data(data)

    async def _write_loop(self, process) -> None:
        assert self._input_queue is not None
        while not self._stop_event.is_set():
            data = await self._input_queue.get()
            if data is None:
                process.stdin.write_eof()
                return
            process.stdin.write(data)
            drain = getattr(process.stdin, "drain", None)
            if drain is not None:
                await drain()

    async def _resize_loop(self, process) -> None:
        assert self._resize_queue is not None
        while not self._stop_event.is_set():
            size = await self._resize_queue.get()
            if size is None:
                return
            columns, rows = size
            resize = getattr(process, "change_terminal_size", None)
            if resize is not None:
                resize(columns, rows)

    def _interactive_client_factory(self):
        import asyncssh

        runner = self

        class InteractiveAuthClient(asyncssh.SSHClient):
            def password_auth_requested(self):
                return runner._ask_auth_prompt(
                    AuthPrompt(
                        title="SSH password",
                        prompt="Password:",
                        echo=False,
                        default_response=runner.options.password or "",
                    )
                )

            def kbdint_auth_requested(self):
                return ""

            def kbdint_challenge_received(self, name, instructions, lang, prompts):
                if not prompts:
                    if instructions:
                        runner.on_status(instructions)
                    return []

                responses: list[str] = []
                for prompt, echo in prompts:
                    response = runner._ask_auth_prompt(
                        AuthPrompt(
                            title=name or "SSH authentication",
                            prompt=prompt,
                            instructions=instructions,
                            echo=echo,
                            default_response=runner._default_response_for_prompt(prompt),
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
        if "password" in normalized and self.options.password:
            return self.options.password
        return ""
