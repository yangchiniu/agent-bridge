"""Auto-restart wrapper for the bridge watcher."""

import subprocess
import sys
import time
from datetime import datetime


def run_with_recovery(command: list[str], restart_delay: int = 5, max_restarts: int = 50):
    """Run a command and restart it on exit.

    Args:
        command: The command to run (e.g., ["python", "-m", "hermes_bridge", "--run"])
        restart_delay: Seconds to wait before restarting
        max_restarts: Maximum number of restarts before giving up (0 = unlimited)
    """
    restarts = 0
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Starting bridge...", flush=True)

        try:
            proc = subprocess.run(command)
            exit_code = proc.returncode
        except KeyboardInterrupt:
            print("\nStopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"[{timestamp}] Error: {e}", flush=True)
            exit_code = 1

        restarts += 1
        if max_restarts > 0 and restarts >= max_restarts:
            print(f"[{timestamp}] Max restarts ({max_restarts}) reached. Exiting.", flush=True)
            sys.exit(1)

        print(
            f"[{timestamp}] Bridge exited (code {exit_code}). "
            f"Restarting in {restart_delay}s... (restart #{restarts})",
            flush=True,
        )
        time.sleep(restart_delay)


if __name__ == "__main__":
    # Default: run hermes_bridge module
    cmd = [sys.executable, "-m", "hermes_bridge", "--run"]
    if len(sys.argv) > 1:
        cmd = sys.argv[1:]
    run_with_recovery(cmd)
