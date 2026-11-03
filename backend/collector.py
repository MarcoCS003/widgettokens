import os
import sys
import argparse
import logging
from typing import Dict, Any, Optional

from backend.core.db import (
    DEFAULT_DB_PATH,
    init_db,
    insert_events,
    get_state,
    set_state,
)
from backend.core.extractor import (
    DEFAULT_OPENCODE_DB,
    DEFAULT_ANTIGRAVITY_BRAIN_DIR,
    extract_opencode_events,
    extract_antigravity_events,
)

logger = logging.getLogger("widgettokens.collector")


def collect_opencode(
    machine_name: str = "personal",
    target_db_path: Optional[str] = None,
    opencode_db_path: str = DEFAULT_OPENCODE_DB
) -> int:
    """
    Collects new OpenCode events and saves them to target SQLite DB.
    """
    init_db(target_db_path)
    state_key = f"{machine_name}_opencode_last_ms"
    last_ms_str = get_state(state_key, target_db_path)
    last_ms = int(last_ms_str) if last_ms_str and last_ms_str.isdigit() else 0

    events = []
    max_ms = last_ms
    for ev in extract_opencode_events(db_path=opencode_db_path, machine_name=machine_name, since_time_created=last_ms):
        events.append(ev)
        # Parse ms from raw_json if available
        try:
            raw = ev.get("raw_json")
            if raw:
                import json
                meta = json.loads(raw)
                ms = int(meta.get("ms_created", 0))
                if ms > max_ms:
                    max_ms = ms
        except Exception:
            pass

    inserted = insert_events(events, target_db_path)
    if max_ms > last_ms:
        set_state(state_key, str(max_ms), target_db_path)

    logger.info("OpenCode collection: %d events found, %d inserted (watermark: %d)", len(events), inserted, max_ms)
    return inserted


def collect_antigravity(
    machine_name: str = "personal",
    target_db_path: Optional[str] = None,
    brain_dir: str = DEFAULT_ANTIGRAVITY_BRAIN_DIR
) -> int:
    """
    Collects new Antigravity events and saves them to target SQLite DB.
    """
    init_db(target_db_path)
    state_key = f"{machine_name}_antigravity_last_ts"
    last_ts = get_state(state_key, target_db_path) or ""

    events = []
    max_ts = last_ts
    for ev in extract_antigravity_events(brain_dir=brain_dir, machine_name=machine_name, since_timestamp=last_ts):
        events.append(ev)
        ts = ev.get("timestamp", "")
        if ts > max_ts:
            max_ts = ts

    inserted = insert_events(events, target_db_path)
    if max_ts > last_ts:
        set_state(state_key, max_ts, target_db_path)

    logger.info("Antigravity collection: %d events found, %d inserted (watermark: %s)", len(events), inserted, max_ts)
    return inserted


def collect_all(
    machine_name: str = "personal",
    target_db_path: Optional[str] = None,
    opencode_db_path: str = DEFAULT_OPENCODE_DB,
    brain_dir: str = DEFAULT_ANTIGRAVITY_BRAIN_DIR
) -> Dict[str, int]:
    """
    Runs both collectors and returns count summary.
    """
    opencode_count = collect_opencode(
        machine_name=machine_name,
        target_db_path=target_db_path,
        opencode_db_path=opencode_db_path
    )
    antigravity_count = collect_antigravity(
        machine_name=machine_name,
        target_db_path=target_db_path,
        brain_dir=brain_dir
    )
    return {
        "opencode_inserted": opencode_count,
        "antigravity_inserted": antigravity_count,
        "total_inserted": opencode_count + antigravity_count
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="WidgetTokens Local Collector")
    parser.add_argument("--machine", default=os.getenv("WIDGETTOKENS_MACHINE", "personal"), help="Machine name ('personal' or 'work')")
    parser.add_argument("--db", default=os.getenv("WIDGETTOKENS_DB", DEFAULT_DB_PATH), help="Target SQLite DB path")
    parser.add_argument("--opencode-db", default=DEFAULT_OPENCODE_DB, help="OpenCode DB path")
    parser.add_argument("--brain-dir", default=DEFAULT_ANTIGRAVITY_BRAIN_DIR, help="Antigravity brain dir")

    args = parser.parse_args()
    summary = collect_all(
        machine_name=args.machine,
        target_db_path=args.db,
        opencode_db_path=args.opencode_db,
        brain_dir=args.brain_dir
    )
    print(f"Collection complete: {summary}")
