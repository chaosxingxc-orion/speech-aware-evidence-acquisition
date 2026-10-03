"""Private own-app credential pipe for the admitted subscription transport."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

from .system_text_policy import PolicyError


_CREDENTIAL_ERRORS = {
    "adapter-unreadable": "own-app credential adapter is unreadable",
    "adapter-pin-mismatch": "own-app credential adapter changed",
    "pipe-timeout": "own-app credential pipe timed out",
    "pipe-os-error": "own-app credential pipe could not start",
    "pipe-execution-error": "own-app credential pipe execution failed",
    "pipe-exit-nonzero": "own-app credential pipe exited unsuccessfully",
    "pipe-response-non-ascii": "invalid own-app credential response encoding",
    "pipe-response-invalid": "invalid own-app credential response shape",
    "callback-unclassified": "registered credential callback failed without a safe category",
}


class CredentialFailure(PolicyError):
    """Carry only a fixed local failure category; never child output or headers."""

    def __init__(self, category, *, transport=False):
        self.category = category if isinstance(category, str) and category in _CREDENTIAL_ERRORS else "callback-unclassified"
        super().__init__("registered credential unavailable" if transport else _CREDENTIAL_ERRORS[self.category])


def safe_credential_failure(error):
    """Map only our exact error type and allowlisted category to public metadata."""
    category = error.category if type(error) is CredentialFailure else "callback-unclassified"
    if not isinstance(category, str) or category not in _CREDENTIAL_ERRORS:
        category = "callback-unclassified"
    return {"category": category, "phase": "before-http-post", "http_post_entered": False}


class SubscriptionBearer:
    """Keep tokens inside host processes; never serialize them into experiment logs."""

    def __init__(self, *, node, script_windows, script_local, script_sha256, app_root_windows=None):
        self.node, self.script_windows = str(node), str(script_windows)
        self.script_local, self.script_sha256 = Path(script_local), script_sha256
        self.app_root_windows = app_root_windows

    def __call__(self):
        try:
            actual_hash = hashlib.sha256(self.script_local.read_bytes()).hexdigest()
        except OSError:
            raise CredentialFailure("adapter-unreadable") from None
        if actual_hash != self.script_sha256:
            raise CredentialFailure("adapter-pin-mismatch")
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
        except subprocess.TimeoutExpired:
            raise CredentialFailure("pipe-timeout") from None
        except OSError:
            raise CredentialFailure("pipe-os-error") from None
        except subprocess.SubprocessError:
            raise CredentialFailure("pipe-execution-error") from None
        # Never include child stdout/stderr in an exception or a research receipt.
        if result.returncode != 0:
            raise CredentialFailure("pipe-exit-nonzero")
        try:
            token = result.stdout.decode("ascii")
        except UnicodeError:
            raise CredentialFailure("pipe-response-non-ascii") from None
        if not (1 <= len(token) <= 32768 and not any(c.isspace() for c in token)
                and not token.startswith(("{", "["))):
            raise CredentialFailure("pipe-response-invalid")
        return token
