"""Pluggable transport layer for message delivery."""

from abc import ABC, abstractmethod
from pathlib import Path


class Transport(ABC):
    """Base class for message transports."""

    @abstractmethod
    def send(self, local_path: Path, remote_dir: Path) -> bool:
        """Send a file to the remote inbox."""
        ...

    @abstractmethod
    def is_reachable(self) -> bool:
        """Check if the remote side is reachable."""
        ...

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
