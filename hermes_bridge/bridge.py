"""Core bridge — inbox watcher and message dispatcher."""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .message import Message, MessageType
from .classifier import Classifier
from .transport.base import Transport
from .agent import Agent

logger = logging.getLogger("hermes-bridge")


class MessageHandler(FileSystemEventHandler):
    """Handles new files in the inbox directory."""

    def __init__(self, bridge: "Bridge"):
        self.bridge = bridge

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix != ".json":
            return
        if Classifier().is_noise(path.name):
            return
        # Small delay to ensure file is fully written
        time.sleep(0.3)
        self.bridge.process_message(path)


class Bridge:
    """The core bridge: watches inbox, classifies, dispatches."""

    def __init__(
        self,
        name: str,
        inbox_dir: Path,
        outbox_dir: Path,
        archive_dir: Path,
        transport: Transport,
        agent: Agent,
        classifier: Classifier = None,
        agent_timeout: int = 180,
        on_reply=None,
    ):
        self.name = name
        self.inbox_dir = Path(inbox_dir)
        self.outbox_dir = Path(outbox_dir)
        self.archive_dir = Path(archive_dir)
        self.transport = transport
        self.agent = agent
        self.classifier = classifier or Classifier()
        self.agent_timeout = agent_timeout
        self.on_reply = on_reply  # callback(reply_path: Path)

        # Ensure directories exist
        for d in [self.inbox_dir, self.outbox_dir, self.archive_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def send(self, content: str, to_agent: str, msg_type: MessageType = MessageType.CHAT) -> Path:
        """Send a message to the remote agent."""
        msg = Message(
            content=content,
            from_agent=self.name,
            to_agent=to_agent,
            msg_type=msg_type,
        )
        local_path = msg.save(self.outbox_dir)
        if self.transport.send(local_path, self.inbox_dir):
            logger.info(f"Sent {msg.id} to {to_agent}")
            return local_path
        else:
            logger.error(f"Failed to send {msg.id}")
            return local_path

    def process_message(self, path: Path):
        """Process a single incoming message."""
        try:
            msg = Message.from_file(path)
        except Exception as e:
            logger.error(f"Failed to parse {path.name}: {e}")
            path.rename(self.archive_dir / path.name)
            return

        logger.info(f"Processing [{msg.msg_type.value}] from {msg.from_agent}: {msg.content[:80]}")

        strategy = self.classifier.classify(msg.content, msg.msg_type.value)

        if strategy == "ignore":
            logger.info(f"Ignored: {msg.id}")
            path.rename(self.archive_dir / path.name)
            return

        if strategy == "auto":
            logger.info(f"Auto-acknowledged: {msg.id}")
            if msg.msg_type == MessageType.TASK.value:
                reply = msg.create_reply(f"Task acknowledged by {self.name}", self.name)
                reply_path = reply.save(self.outbox_dir)
                self.transport.send(reply_path, self.inbox_dir)
            path.rename(self.archive_dir / path.name)
            return

        # strategy == "agent" — invoke the LLM agent
        prompt = f"[Message from {msg.from_agent}]\n\n{msg.content}"
        response = self.agent.invoke(prompt, timeout=self.agent_timeout)

        if response:
            reply = msg.create_reply(response, self.name)
            reply_path = reply.save(self.outbox_dir)
            self.transport.send(reply_path, self.inbox_dir)
            logger.info(f"Replied to {msg.id} ({len(response)} chars)")
            if self.on_reply:
                self.on_reply(reply_path)
        else:
            logger.warning(f"Agent invocation failed for {msg.id}")

        path.rename(self.archive_dir / path.name)

    def scan_existing(self):
        """Process any messages already in the inbox."""
        files = sorted(self.inbox_dir.glob("*.json"))
        if files:
            logger.info(f"Found {len(files)} existing messages")
            for f in files:
                if not self.classifier.is_noise(f.name):
                    self.process_message(f)

    def run(self):
        """Start the watcher loop."""
        logger.info(f"=== Hermes Bridge v0.1 — {self.name} ===")
        logger.info(f"  Inbox:   {self.inbox_dir}")
        logger.info(f"  Outbox:  {self.outbox_dir}")
        logger.info(f"  Archive: {self.archive_dir}")
        logger.info(f"  Transport: {self.transport}")
        logger.info(f"  Agent: {self.agent}")

        self.scan_existing()

        observer = Observer()
        observer.schedule(MessageHandler(self), str(self.inbox_dir), recursive=False)
        observer.start()
        logger.info("Watching for new messages...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            observer.stop()
        observer.join()
