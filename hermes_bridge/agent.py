"""Agent interface — pluggable agent invocation."""

import subprocess
import sys
from abc import ABC, abstractmethod


class Agent(ABC):
    """Base class for agent backends."""

    @abstractmethod
    def invoke(self, prompt: str, timeout: int = 180) -> str | None:
        """Send a prompt to the agent and return the response."""
        ...


class HermesAgent(Agent):
    """Invoke Hermes Agent via CLI."""

    def __init__(self, command: str = "hermes", extra_args: list[str] = None):
        self.command = command
        self.extra_args = extra_args or []

    def invoke(self, prompt: str, timeout: int = 180) -> str | None:
        cmd = [self.command, "chat", "-q", prompt, "-Q"] + self.extra_args
        kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        try:
            proc = subprocess.Popen(cmd, **kwargs)
            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
            if proc.returncode == 0 and stdout_bytes:
                raw = stdout_bytes.decode("utf-8", errors="replace")
                return self._extract(raw)
            return None
        except subprocess.TimeoutExpired:
            return None

    @staticmethod
    def _extract(raw: str) -> str:
        """Extract reply from hermes chat -Q output."""
        lines = raw.strip().split("\n")
        # Skip session_id line
        if lines and lines[0].startswith("session_id:"):
            lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
        return "\n".join(lines).strip()


class CLIAgent(Agent):
    """Invoke any CLI command as an agent."""

    def __init__(self, command: list[str]):
        self.command = command

    def invoke(self, prompt: str, timeout: int = 180) -> str | None:
        cmd = self.command + [prompt]
        kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        try:
            proc = subprocess.Popen(cmd, **kwargs)
            stdout_bytes, _ = proc.communicate(timeout=timeout)
            if proc.returncode == 0 and stdout_bytes:
                return stdout_bytes.decode("utf-8", errors="replace").strip()
            return None
        except subprocess.TimeoutExpired:
            return None
