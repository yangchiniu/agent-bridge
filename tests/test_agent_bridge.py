"""Unit tests for agent_bridge."""

import json
import tempfile
from pathlib import Path

import pytest

from agent_bridge.message import Message, MessageType
from agent_bridge.classifier import Classifier, ClassifierConfig


# ── Message ──────────────────────────────────────────────────────────────

class TestMessage:
    def test_create_default(self):
        msg = Message(content="hello", from_agent="A", to_agent="B")
        assert msg.content == "hello"
        assert msg.from_agent == "A"
        assert msg.to_agent == "B"
        assert msg.msg_type == MessageType.CHAT
        assert msg.id.startswith("msg-")

    def test_to_json_roundtrip(self):
        msg = Message(
            content="test message",
            from_agent="Agent-A",
            to_agent="Agent-B",
            msg_type=MessageType.TASK,
        )
        json_str = msg.to_json()
        data = json.loads(json_str)
        restored = Message.from_json(data)

        assert restored.content == msg.content
        assert restored.from_agent == msg.from_agent
        assert restored.to_agent == msg.to_agent
        assert restored.msg_type == msg.msg_type
        assert restored.id == msg.id

    def test_save_and_load(self):
        msg = Message(content="file test", from_agent="A", to_agent="B")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = msg.save(Path(tmpdir))
            assert path.exists()
            loaded = Message.from_file(path)
            assert loaded.content == msg.content
            assert loaded.id == msg.id

    def test_create_reply(self):
        msg = Message(content="question?", from_agent="A", to_agent="B")
        reply = msg.create_reply("answer!", from_agent="B")

        assert reply.content == "answer!"
        assert reply.from_agent == "B"
        assert reply.to_agent == "A"
        assert reply.reply_to == msg.id
        assert reply.msg_type == MessageType.REPORT

    def test_unicode_content(self):
        msg = Message(content="你好世界 🌍", from_agent="A", to_agent="B")
        json_str = msg.to_json()
        data = json.loads(json_str)
        restored = Message.from_json(data)
        assert restored.content == "你好世界 🌍"


# ── Classifier ──────────────────────────────────────────────────────────

class TestClassifier:
    def test_short_auto(self):
        c = Classifier()
        assert c.classify("收到") == "auto"

    def test_long_agent(self):
        c = Classifier()
        long_msg = "请帮我检查一下部署状态，然后运行测试套件，最后把结果发回来" * 5
        assert c.classify(long_msg) == "agent"

    def test_keyword_agent(self):
        c = Classifier()
        assert c.classify("帮我查一下日志") == "agent"
        assert c.classify("为什么服务挂了") == "agent"
        assert c.classify("deploy the service") == "agent"

    def test_report_auto(self):
        c = Classifier()
        assert c.classify("any content", msg_type="report") == "auto"

    def test_ack_auto(self):
        c = Classifier()
        assert c.classify("any content", msg_type="ack") == "auto"

    def test_task_agent(self):
        c = Classifier()
        assert c.classify("短", msg_type="task") == "agent"

    def test_custom_config(self):
        cfg = ClassifierConfig(
            short_threshold=10,
            long_threshold=50,
            agent_keywords=["特殊"],
            task_keywords=["干活"],
        )
        c = Classifier(cfg)
        assert c.classify("短") == "auto"  # len < 10
        assert c.classify("这是一段比较长的消息内容") == "agent"  # len > 50
        assert c.classify("请特殊处理") == "agent"
        assert c.classify("去干活") == "agent"

    def test_noise_detection(self):
        c = Classifier()
        assert c.is_noise(".DS_Store") is True
        assert c.is_noise("~lock.tmp") is True
        assert c.is_noise("data.tmp") is True
        assert c.is_noise("message.json") is False
        assert c.is_noise("reply-20260725.json") is False

    def test_from_dict(self):
        cfg = ClassifierConfig.from_dict({"short_threshold": 100, "agent_keywords": ["请"]})
        assert cfg.short_threshold == 100
        assert cfg.agent_keywords == ["请"]
        # Defaults preserved
        assert cfg.long_threshold == 200


# ── Integration: two bridges via shared folder ──────────────────────────

class TestSharedTransport:
    """Test SharedTransport with real filesystem operations."""

    def test_send(self):
        from agent_bridge.transport.shared import SharedTransport

        with tempfile.TemporaryDirectory() as tmpdir:
            shared = Path(tmpdir) / "shared_inbox"
            shared.mkdir()

            transport = SharedTransport(shared_inbox=shared)

            msg = Message(content="hello", from_agent="A", to_agent="B")
            with tempfile.TemporaryDirectory() as outbox:
                path = msg.save(Path(outbox))
                assert transport.send(path, shared) is True
                assert (shared / path.name).exists()

    def test_is_reachable(self):
        from agent_bridge.transport.shared import SharedTransport

        with tempfile.TemporaryDirectory() as tmpdir:
            shared = Path(tmpdir) / "exists"
            shared.mkdir()
            assert SharedTransport(shared_inbox=shared).is_reachable() is True

            assert SharedTransport(shared_inbox=Path(tmpdir) / "nope").is_reachable() is False


class TestAgent:
    """Test agent interface (without actually calling Hermes)."""

    def test_hermes_agent_extract(self):
        from agent_bridge.agent import HermesAgent

        raw = "session_id: abc123\nThis is the reply\nwith multiple lines."
        result = HermesAgent._extract(raw)
        assert result == "This is the reply\nwith multiple lines."

    def test_hermes_agent_extract_skip_blanks(self):
        from agent_bridge.agent import HermesAgent

        raw = "session_id: abc123\n\n\n  Reply here."
        result = HermesAgent._extract(raw)
        assert result == "Reply here."
