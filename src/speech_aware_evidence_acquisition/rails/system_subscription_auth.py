"""Private own-app credential pipe for the admitted subscription transport."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

from .system_text_policy import PolicyError, require


class SubscriptionBearer:
    """Keep tokens inside host processes; never serialize them into experiment logs."""

    def __init__(self, *, node, script_windows, script_local, script_sha256, app_root_windows=None):
        self.node, self.script_windows = str(node), str(script_windows)
        self.script_local, self.script_sha256 = Path(script_local), script_sha256
        self.app_root_windows = app_root_windows

    def __call__(self):
        require(hashlib.sha256(self.script_local.read_bytes()).hexdigest() == self.script_sha256,
                "own-app credential adapter changed")
        env = {k: v for k, v in os.environ.items() if k.upper() in {
            "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA",
            "APPDATA", "PROGRAMDATA", "COMSPEC", "PATHEXT", "WSLENV"}}
        env["SAEA_AUTH_INTERNAL_PIPE"] = "1"
        # WSL only transfers explicitly listed variables to Windows child processes.
        names = [p for p in env.get("WSLENV", "").split(":") if p.startswith("SAEA_AUTH_INTERNAL_PIPE")]
        if not names:
            env["WSLENV"] = env.get("WSLENV", "") + ":SAEA_AUTH_INTERNAL_PIPE"
        try:
            command = [self.node, self.script_windows, "credential-pipe"]
            if self.app_root_windows is not None:
                command.append(self.app_root_windows)
            result = subprocess.run(command,
                input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                timeout=90, check=False)
        except (OSError, subprocess.SubprocessError):
            raise PolicyError("own-app credential pipe unavailable") from None
        # Never include child stdout/stderr in an exception or a research receipt.
        require(result.returncode == 0, "own-app sign-in or credential renewal required")
        try:
            token = result.stdout.decode("ascii")
        except UnicodeError:
            raise PolicyError("invalid own-app credential response") from None
        require(1 <= len(token) <= 32768 and not any(c.isspace() for c in token)
                and not token.startswith(("{", "[")), "invalid own-app credential response")
        return token
