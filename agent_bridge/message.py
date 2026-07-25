"""Message protocol for agent-to-agent communication."""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class MessageType(str, Enum):
    CHAT = "chat"           # Conversational message, needs agent reply
    TASK = "task"           # Action request, execute and report back
    REPORT = "report"       # Status/result report, auto-acknowledge
    ACK = "ack"             # Acknowledgement receipt


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    URGENT = "urgent"


@dataclass
class Message:
    content: str
    from_agent: str
    to_agent: str
    msg_type: MessageType = MessageType.CHAT
    priority: MessagePriority = MessagePriority.NORMAL
    id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reply_to: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        data = {
            "id": self.id,
            "from": self.from_agent,
            "to": self.to_agent,
            "timestamp": self.timestamp,
            "type": self.msg_type.value,
            "priority": self.priority.value,
            "content": self.content,
        }
        if self.reply_to:
            data["reply_to"] = self.reply_to
        if self.metadata:
            data["metadata"] = self.metadata
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, data: dict) -> "Message":
        return cls(
            id=data.get("id", f"msg-{uuid.uuid4().hex[:12]}"),
            from_agent=data.get("from", "unknown"),
            to_agent=data.get("to", "unknown"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            msg_type=MessageType(data.get("type", "chat")),
            priority=MessagePriority(data.get("priority", "normal")),
            content=data.get("content", ""),
            reply_to=data.get("reply_to"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_file(cls, path: Path) -> "Message":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_json(data)

    def save(self, directory: Path) -> Path:
        path = directory / f"{self.id}.json"
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    def create_reply(self, content: str, from_agent: str) -> "Message":
        return Message(
            content=content,
            from_agent=from_agent,
            to_agent=self.from_agent,
            msg_type=MessageType.REPORT,
            reply_to=self.id,
        )
