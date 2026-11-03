import os
import sys
import json
import time
import argparse
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Optional

from backend.core.db import (
    DEFAULT_DB_PATH,
    init_db,
    get_events_delta,
    get_aggregated_matrix,
    get_state,
    set_state,
)
from backend.collector import collect_all

DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/plasma-tokens")
DEFAULT_CACHE_PATH = os.path.join(DEFAULT_CACHE_DIR, "history.json")
DEFAULT_SERVER_URL = "http://127.0.0.1:8765"

logger = logging.getLogger("widgettokens.syncer")


def _atomic_write_json(file_path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    temp_path = f"{file_path}.tmp.{os.getpid()}"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, file_path)


def sync_cycle(
    server_url: str = DEFAULT_SERVER_URL,
    client_db_path: Optional[str] = None,
    cache_file_path: str = DEFAULT_CACHE_PATH,
    machine_name: str = "personal",
    skip_collection: bool = False
) -> bool:
    """
    Executes a single synchronization cycle:
    1. Collects local tokens (if not skipped).
    2. Sends deltas to server via POST /api/sync.
    3. Fetches consolidated 365-day history via GET /api/tokens.
    4. Writes history to cache_file_path.
    5. Gracefully falls back if server is unreachable (offline mode).
    """
    init_db(client_db_path)

    if not skip_collection:
        try:
            collect_all(machine_name=machine_name, target_db_path=client_db_path)
        except Exception as e:
            logger.warning("Local collection encountered an error: %s", e)

    server_base = server_url.rstrip("/")
    sync_state_key = f"{machine_name}_last_synced_timestamp"
    last_synced_ts = get_state(sync_state_key, client_db_path) or "1970-01-01T00:00:00Z"

    # Query local deltas to send to central server
    deltas = get_events_delta(
        since_timestamp=last_synced_ts,
        machine=machine_name,
        db_path=client_db_path
    )

    # Attempt push deltas to server
    try:
        if deltas:
            payload = {
                "machine": machine_name,
                "events": deltas
            }
            body_bytes = json.dumps(payload).encode("utf-8")
            req = Request(
                f"{server_base}/api/sync",
                data=body_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logger.info("Sent %d deltas to server successfully", len(deltas))
                    # Update watermark timestamp to the newest event sent
                    newest_ts = max(d["timestamp"] for d in deltas)
                    set_state(sync_state_key, newest_ts, client_db_path)

        # Fetch consolidated matrix (365 days)
        req_get = Request(f"{server_base}/api/tokens?days=365")
        with urlopen(req_get, timeout=10) as resp:
            if resp.status == 200:
                raw_json = resp.read().decode("utf-8")
                matrix_data = json.loads(raw_json)
                _atomic_write_json(cache_file_path, matrix_data)
                logger.info("Updated cache from server: %s", cache_file_path)
                return True

    except (URLError, HTTPError, TimeoutError, OSError) as e:
        logger.warning("Server unreachable (%s: %s). Running in offline fallback mode.", server_url, e)

        # Offline fallback: if cache does not exist, build it from local SQLite DB
        if not os.path.exists(cache_file_path):
            try:
                local_matrix = get_aggregated_matrix(days=365, db_path=client_db_path)
                _atomic_write_json(cache_file_path, local_matrix)
                logger.info("Generated initial offline cache from local database: %s", cache_file_path)
            except Exception as le:
                logger.error("Failed to generate offline cache: %s", le)

    return False


def run_syncer_loop(
    server_url: str = DEFAULT_SERVER_URL,
    client_db_path: Optional[str] = None,
    cache_file_path: str = DEFAULT_CACHE_PATH,
    machine_name: str = "personal",
    interval: int = 300
) -> None:
    logger.info("Starting WidgetTokens Syncer (Server: %s, Interval: %ds, Machine: %s)", server_url, interval, machine_name)
    while True:
        try:
            sync_cycle(
                server_url=server_url,
                client_db_path=client_db_path,
                cache_file_path=cache_file_path,
                machine_name=machine_name
            )
        except Exception as e:
            logger.error("Unexpected error in syncer loop: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="WidgetTokens Syncer Client")
    parser.add_argument("--server", default=os.getenv("WIDGETTOKENS_SERVER_URL", DEFAULT_SERVER_URL), help="Central Server URL (Tailscale IP:Port)")
    parser.add_argument("--machine", default=os.getenv("WIDGETTOKENS_MACHINE", "personal"), help="Machine name ('personal' or 'work')")
    parser.add_argument("--db", default=os.getenv("WIDGETTOKENS_DB", DEFAULT_DB_PATH), help="Local SQLite DB path")
    parser.add_argument("--cache", default=os.getenv("WIDGETTOKENS_CACHE", DEFAULT_CACHE_PATH), help="Plasmoid cache JSON path")
    parser.add_argument("--interval", type=int, default=int(os.getenv("WIDGETTOKENS_INTERVAL", "300")), help="Sync interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit immediately")

    args = parser.parse_args()

    if args.once:
        success = sync_cycle(
            server_url=args.server,
            client_db_path=args.db,
            cache_file_path=args.cache,
            machine_name=args.machine
        )
        sys.exit(0 if success else 1)
    else:
        run_syncer_loop(
            server_url=args.server,
            client_db_path=args.db,
            cache_file_path=args.cache,
            machine_name=args.machine,
            interval=args.interval
        )
