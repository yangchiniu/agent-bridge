"""Configurable message classifier."""

from dataclasses import dataclass, field
from typing import Optional

from .message import MessageType


@dataclass
class ClassifierConfig:
    """Classification rules. All keyword lists are optional."""

    # Content length threshold — messages shorter than this are "auto"
    short_threshold: int = 50

    # Content length threshold — messages longer than this are "agent"
    long_threshold: int = 200

    # Keywords that indicate the message needs agent reasoning
    agent_keywords: list[str] = field(default_factory=lambda: [
        "问", "查", "怎么", "为什么", "帮我", "请", "解释", "分析",
        "think", "analyze", "explain", "help", "what", "why", "how",
    ])

    # Keywords that indicate a task request
    task_keywords: list[str] = field(default_factory=lambda: [
        "执行", "运行", "部署", "安装", "配置", "修复", "创建", "删除",
        "run", "deploy", "fix", "install", "set up", "create", "delete",
    ])

    # Noise filename prefixes (temp files, system files)
    noise_prefixes: tuple[str, ...] = (".", "~", "Thumbs.db", "desktop.ini")

    # Noise filename suffixes
    noise_suffixes: tuple[str, ...] = (".tmp", ".swp", ".partial")

    @classmethod
    def from_dict(cls, d: dict) -> "ClassifierConfig":
        """Load from a dict (e.g. from YAML config)."""
        cfg = cls()
        for key, value in d.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg


class Classifier:
    """Classify incoming messages and determine handling strategy."""

    def __init__(self, config: ClassifierConfig = None):
        self.config = config or ClassifierConfig()

    def classify(self, content: str, msg_type: str = None) -> str:
        """Determine handling strategy for a message.

        Returns:
            "agent"  — needs LLM agent processing
            "auto"   — can be handled programmatically
            "ignore" — should be silently skipped
        """
        cfg = self.config

        # Explicit type overrides
        if msg_type == MessageType.ACK.value:
            return "auto"
        if msg_type == MessageType.REPORT.value:
            return "auto"
        if msg_type == MessageType.TASK.value:
            return "agent"

        # Length-based heuristics
        if len(content) > cfg.long_threshold:
            return "agent"

        content_lower = content.lower()

        if any(kw in content_lower for kw in cfg.agent_keywords):
            return "agent"

        if any(kw in content_lower for kw in cfg.task_keywords):
            return "agent"

        if len(content) < cfg.short_threshold:
            return "auto"

        return "agent"

    def is_noise(self, filename: str) -> bool:
        """Check if a filename should be ignored."""
        cfg = self.config
        return (
            any(filename.startswith(p) for p in cfg.noise_prefixes)
            or any(filename.endswith(s) for s in cfg.noise_suffixes)
        )
