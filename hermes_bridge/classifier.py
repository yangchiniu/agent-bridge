"""Message classification rules."""

from .message import MessageType


class Classifier:
    """Classify incoming messages and determine handling strategy."""

    # Keywords that trigger agent processing (CHAT)
    AGENT_KEYWORDS = {"问", "查", "怎么", "为什么", "帮我", "请", "think", "analyze", "explain"}

    # Keywords that indicate task requests
    TASK_KEYWORDS = {"执行", "运行", "部署", "安装", "配置", "修复", "run", "deploy", "fix", "install", "set up"}

    def classify(self, content: str, msg_type: str = None) -> str:
        """Determine handling strategy for a message.

        Returns:
            "agent"  — needs LLM agent processing
            "auto"   — can be handled programmatically
            "ignore" — should be silently skipped
        """
        # If type is explicitly set, honor it
        if msg_type == MessageType.ACK.value:
            return "auto"

        if msg_type == MessageType.REPORT.value:
            return "auto"

        if msg_type == MessageType.TASK.value:
            return "agent"

        # Content-based heuristics for CHAT messages
        if len(content) > 200:
            return "agent"  # Long messages likely need reasoning

        content_lower = content.lower()
        if any(kw in content_lower for kw in self.AGENT_KEYWORDS):
            return "agent"

        if any(kw in content_lower for kw in self.TASK_KEYWORDS):
            return "agent"

        # Short informational messages can be auto-acknowledged
        if len(content) < 50:
            return "auto"

        return "agent"

    def is_noise(self, filename: str) -> bool:
        """Check if a filename should be ignored (temp files, system files)."""
        noise_prefixes = (".", "~", "Thumbs.db", "desktop.ini")
        noise_suffixes = (".tmp", ".swp", ".partial")
        return (
            any(filename.startswith(p) for p in noise_prefixes)
            or any(filename.endswith(s) for s in noise_suffixes)
        )
