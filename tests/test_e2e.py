"""End-to-end test: two Bridge instances communicating via shared folders."""

import tempfile
import threading
import time
from pathlib import Path

from agent_bridge.bridge import Bridge
from agent_bridge.message import Message, MessageType
from agent_bridge.classifier import Classifier
from agent_bridge.transport.shared import SharedTransport
from agent_bridge.agent import Agent


class MockAgent(Agent):
    """A mock agent that echoes back the prompt."""

    def __init__(self, responses: dict[str, str] = None):
        self.responses = responses or {}
        self.calls = []

    def invoke(self, prompt: str, timeout: int = 180) -> str | None:
        self.calls.append(prompt)
        for key, response in self.responses.items():
            if key in prompt:
                return response
        return f"Echo: {prompt}"


def test_two_bridges_communicate():
    """Two Bridge instances send and receive messages via shared folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Shared directories (simulating shared filesystem)
        a_to_b_inbox = base / "b-inbox"  # A writes here, B watches
        b_to_a_inbox = base / "a-inbox"  # B writes here, A watches
        a_to_b_inbox.mkdir()
        b_to_a_inbox.mkdir()

        # Agent A's local directories
        a_inbox = base / "a" / "inbox"
        a_outbox = base / "a" / "outbox"
        a_archive = base / "a" / "archive"

        # Agent B's local directories
        b_inbox = base / "b" / "inbox"
        b_outbox = base / "b" / "outbox"
        b_archive = base / "b" / "archive"

        mock_a = MockAgent(responses={"ping": "pong from A"})
        mock_b = MockAgent(responses={"hello": "hi from B"})

        bridge_a = Bridge(
            name="Agent-A",
            inbox_dir=a_inbox,
            outbox_dir=a_outbox,
            archive_dir=a_archive,
            transport=SharedTransport(shared_inbox=a_to_b_inbox),
            agent=mock_a,
            classifier=Classifier(),
        )

        bridge_b = Bridge(
            name="Agent-B",
            inbox_dir=b_inbox,
            outbox_dir=b_outbox,
            archive_dir=b_archive,
            transport=SharedTransport(shared_inbox=b_to_a_inbox),
            agent=mock_b,
            classifier=Classifier(),
        )

        # A sends a message to B (long enough to trigger agent processing)
        bridge_a.send("hello from A, please help me check the deployment status and run tests", "Agent-B")

        # Verify the message landed in B's inbox (via shared folder)
        inbox_files = list(a_to_b_inbox.glob("*.json"))
        assert len(inbox_files) == 1

        # Move it to B's actual inbox (simulating the shared transport)
        msg_file = inbox_files[0]
        (b_inbox / msg_file.name).write_text(msg_file.read_text())

        # B processes the message
        bridge_b.scan_existing()

        # Verify B's agent was called
        assert len(mock_b.calls) == 1
        assert "hello from A" in mock_b.calls[0]

        # Verify B sent a reply
        outbox_files = list(b_outbox.glob("*.json"))
        assert len(outbox_files) == 1

        # Verify the reply content
        reply = Message.from_file(outbox_files[0])
        assert reply.content == "hi from B"
        assert reply.from_agent == "Agent-B"
        assert reply.to_agent == "Agent-A"
        assert reply.reply_to is not None

        # Verify the original message was archived
        assert len(list(b_archive.glob("*.json"))) == 1
        assert len(list(b_inbox.glob("*.json"))) == 0


def test_auto_acknowledge_report():
    """REPORT messages are auto-acknowledged without calling the agent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        inbox = base / "inbox"
        outbox = base / "outbox"
        archive = base / "archive"
        shared = base / "shared"
        shared.mkdir()

        mock = MockAgent()

        bridge = Bridge(
            name="TestAgent",
            inbox_dir=inbox,
            outbox_dir=outbox,
            archive_dir=archive,
            transport=SharedTransport(shared_inbox=shared),
            agent=mock,
        )

        # Create a REPORT message directly in inbox
        report = Message(
            content="deployment complete",
            from_agent="Remote",
            to_agent="TestAgent",
            msg_type=MessageType.REPORT,
        )
        report.save(inbox)

        # Process
        bridge.scan_existing()

        # Agent should NOT have been called
        assert len(mock.calls) == 0

        # Message should be archived
        assert len(list(archive.glob("*.json"))) == 1
