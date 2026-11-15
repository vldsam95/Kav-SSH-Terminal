from __future__ import annotations

from ssh.sftp_client import RemoteFile
from ui.sftp_panel import SftpPanel


def test_sftp_panel_translates_shell_home_to_sftp_path() -> None:
    assert SftpPanel._request_path("~") == "."
    assert SftpPanel._request_path("~/logs") == "./logs"
    assert SftpPanel._request_path("/var/www") == "/var/www"


def test_sftp_panel_parent_paths() -> None:
    assert SftpPanel._parent_path("~/logs/nginx") == "~/logs"
    assert SftpPanel._parent_path("./logs") == "."
    assert SftpPanel._parent_path("/var/www") == "/var"


def test_sftp_panel_formats_sizes() -> None:
    assert SftpPanel._display_size(RemoteFile("dir", "dir", 4096, True)) == ""
    assert SftpPanel._display_size(RemoteFile("small.txt", "small.txt", 3106, False)) == "3,106 B"
    assert SftpPanel._display_size(RemoteFile("large.log", "large.log", 1048576, False)) == "1.0 MB"


def test_sftp_panel_builds_upload_remote_path() -> None:
    assert SftpPanel._remote_child_path(".", "file.txt") == "./file.txt"
    assert SftpPanel._remote_child_path("./logs", "file.txt") == "./logs/file.txt"
    assert SftpPanel._remote_child_path("/var/www", "file.txt") == "/var/www/file.txt"


def test_remote_file_model_supports_hebrew_names() -> None:
    file = RemoteFile(name="שלום.txt", path="/tmp/שלום.txt", size=12, is_dir=False)

    assert file.name == "שלום.txt"
    assert file.path.endswith("שלום.txt")
