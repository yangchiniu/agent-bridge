"""Shared folder transport (SMB/NFS/9p/NAS)."""

import shutil
from pathlib import Path

from .base import Transport


class SharedTransport(Transport):
    """Send messages via shared filesystem (copy to shared directory)."""

    def __init__(self, shared_inbox: Path):
        self.shared_inbox = Path(shared_inbox)

    def send(self, local_path: Path, remote_dir: Path) -> bool:
        try:
            dest = self.shared_inbox / local_path.name
            shutil.copy2(str(local_path), str(dest))
            return True
        except Exception:
            return False

    def is_reachable(self) -> bool:
        return self.shared_inbox.exists() and self.shared_inbox.is_dir()

    def __repr__(self):
        return f"<SharedTransport {self.shared_inbox}>"
