"""CLI entry point for agent-bridge."""

import argparse
import logging
import sys
from pathlib import Path

from .bridge import Bridge
from .message import MessageType
from .classifier import Classifier, ClassifierConfig
from .transport.scp import SCPTransport
from .transport.shared import SharedTransport
from .agent import HermesAgent, CLIAgent
from .recovery import run_with_recovery


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def load_config(config_path: str) -> dict:
    """Load YAML config file."""
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_bridge(config: dict) -> Bridge:
    """Build a Bridge instance from config."""
    me = config["name"]
    dirs = config["directories"]
    inbox = Path(dirs["inbox"])
    outbox = Path(dirs["outbox"])
    archive = Path(dirs["archive"])

    # Build transport
    transport_cfg = config.get("transport", {"type": "scp"})
    if transport_cfg["type"] == "scp":
        transport = SCPTransport(
            host=transport_cfg["host"],
            user=transport_cfg["user"],
            port=transport_cfg.get("port", 22),
            key=transport_cfg.get("key"),
        )
    elif transport_cfg["type"] == "shared":
        transport = SharedTransport(shared_inbox=Path(transport_cfg["shared_inbox"]))
    else:
        raise ValueError(f"Unknown transport type: {transport_cfg['type']}")

    # Build agent
    agent_cfg = config.get("agent", {"type": "hermes"})
    if agent_cfg["type"] == "hermes":
        agent = HermesAgent(
            command=agent_cfg.get("command", "hermes"),
            extra_args=agent_cfg.get("extra_args", []),
        )
    elif agent_cfg["type"] == "cli":
        agent = CLIAgent(command=agent_cfg["command"])
    else:
        raise ValueError(f"Unknown agent type: {agent_cfg['type']}")

    # Build classifier
    classifier_cfg = ClassifierConfig.from_dict(config.get("classifier", {}))

    return Bridge(
        name=me,
        inbox_dir=inbox,
        outbox_dir=outbox,
        archive_dir=archive,
        transport=transport,
        agent=agent,
        classifier=Classifier(classifier_cfg),
        agent_timeout=config.get("agent_timeout", 180),
    )


def cmd_run(args):
    """Run the bridge watcher."""
    config = load_config(args.config)
    bridge = build_bridge(config)
    bridge.run()


def cmd_send(args):
    """Send a message to the remote agent."""
    config = load_config(args.config)
    bridge = build_bridge(config)
    msg_type = MessageType(args.type)
    path = bridge.send(args.content, args.to, msg_type)
    print(f"Sent: {path.name}")


def cmd_status(args):
    """Show bridge status."""
    config = load_config(args.config)
    dirs = config["directories"]
    for name, path in dirs.items():
        p = Path(path)
        count = len(list(p.glob("*.json"))) if p.exists() else 0
        print(f"  {name}: {p} ({count} messages)")


def main():
    parser = argparse.ArgumentParser(
        prog="hermes-bridge",
        description="LAN peer-to-peer agent communication bridge",
    )
    parser.add_argument("-c", "--config", default="bridge.yaml", help="Config file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    sub = parser.add_subparsers(dest="command")

    # run
    run_parser = sub.add_parser("run", help="Start the bridge watcher")
    run_parser.add_argument("--with-recovery", action="store_true", help="Auto-restart on crash")

    # send
    send_parser = sub.add_parser("send", help="Send a message")
    send_parser.add_argument("content", help="Message content")
    send_parser.add_argument("--to", required=True, help="Remote agent name")
    send_parser.add_argument("--type", default="chat", choices=["chat", "task", "report"], help="Message type")

    # status
    sub.add_parser("status", help="Show bridge status")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "run":
        if args.with_recovery:
            run_with_recovery([sys.executable, "-m", "agent_bridge", "-c", args.config, "run"])
        else:
            cmd_run(args)
    elif args.command == "send":
        cmd_send(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
