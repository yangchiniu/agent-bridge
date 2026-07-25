"""SCP-based transport for cross-machine message delivery."""

import subprocess
from pathlib import Path

from .base import Transport


class SCPTransport(Transport):
    """Send messages via SSH/SCP."""

    def __init__(self, host: str, user: str, port: int = 22, key: str = None):
        self.host = host
        self.user = user
        self.port = port
        self.key = key

    def send(self, local_path: Path, remote_dir: Path) -> bool:
        target = f"{self.user}@{self.host}:{remote_dir}/"
        cmd = ["scp", "-o", "ConnectTimeout=5"]
        if self.port != 22:
            cmd += ["-P", str(self.port)]
        if self.key:
            cmd += ["-i", self.key]
        cmd += [str(local_path), target]
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        return result.returncode == 0

    def is_reachable(self) -> bool:
        cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"{self.user}@{self.host}", "echo ok"
        ]
        if self.port != 22:
            cmd.insert(1, "-p")
            cmd.insert(2, str(self.port))
        if self.key:
            cmd.insert(1, "-i")
            cmd.insert(2, self.key)
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        return result.returncode == 0

    def __repr__(self):
        return f"<SCPTransport {self.user}@{self.host}:{self.port}>"
