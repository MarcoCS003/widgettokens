import os
import sys
import socket
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
    DEFAULT_CLAUDE_DIR,
    DEFAULT_OPENCLAW_DIR,
    extract_opencode_events,
    extract_antigravity_events,
    extract_claude_events,
    extract_openclaw_events,
)

logger = logging.getLogger("widgettokens.collector")


def get_default_machine() -> str:
    return os.getenv("WIDGETTOKENS_MACHINE") or socket.gethostname()


def collect_opencode(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    opencode_db_path: str = DEFAULT_OPENCODE_DB
) -> int:
    mach = machine_name or get_default_machine()
    init_db(target_db_path)
    state_key = f"{mach}_opencode_last_ms"
    last_ms_str = get_state(state_key, target_db_path)
    last_ms = int(last_ms_str) if last_ms_str and last_ms_str.isdigit() else 0

    events = []
    max_ms = last_ms
    for ev in extract_opencode_events(db_path=opencode_db_path, machine_name=mach, since_time_created=last_ms):
        events.append(ev)
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

    logger.info("OpenCode collection [%s]: %d events found, %d inserted", mach, len(events), inserted)
    return inserted


def collect_antigravity(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    brain_dir: str = DEFAULT_ANTIGRAVITY_BRAIN_DIR
) -> int:
    mach = machine_name or get_default_machine()
    init_db(target_db_path)
    state_key = f"{mach}_antigravity_last_ts"
    last_ts = get_state(state_key, target_db_path) or ""

    events = []
    max_ts = last_ts
    for ev in extract_antigravity_events(brain_dir=brain_dir, machine_name=mach, since_timestamp=last_ts):
        events.append(ev)
        ts = ev.get("timestamp", "")
        if ts > max_ts:
            max_ts = ts

    inserted = insert_events(events, target_db_path)
    if max_ts > last_ts:
        set_state(state_key, max_ts, target_db_path)

    logger.info("Antigravity collection [%s]: %d events found, %d inserted", mach, len(events), inserted)
    return inserted


def collect_claude(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    claude_dir: str = DEFAULT_CLAUDE_DIR
) -> int:
    mach = machine_name or get_default_machine()
    init_db(target_db_path)
    state_key = f"{mach}_claude_last_ts"
    last_ts = get_state(state_key, target_db_path) or ""

    events = []
    max_ts = last_ts
    for ev in extract_claude_events(claude_dir=claude_dir, machine_name=mach, since_timestamp=last_ts):
        events.append(ev)
        ts = ev.get("timestamp", "")
        if ts > max_ts:
            max_ts = ts

    inserted = insert_events(events, target_db_path)
    if max_ts > last_ts:
        set_state(state_key, max_ts, target_db_path)

    logger.info("Claude Code collection [%s]: %d events found, %d inserted", mach, len(events), inserted)
    return inserted


def collect_openclaw(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    openclaw_dir: str = DEFAULT_OPENCLAW_DIR
) -> int:
    mach = machine_name or get_default_machine()
    init_db(target_db_path)
    state_key = f"{mach}_openclaw_last_ts"
    last_ts = get_state(state_key, target_db_path) or ""

    events = []
    max_ts = last_ts
    for ev in extract_openclaw_events(openclaw_dir=openclaw_dir, machine_name=mach, since_timestamp=last_ts):
        events.append(ev)
        ts = ev.get("timestamp", "")
        if ts > max_ts:
            max_ts = ts

    inserted = insert_events(events, target_db_path)
    if max_ts > last_ts:
        set_state(state_key, max_ts, target_db_path)

    logger.info("OpenClaw collection [%s]: %d events found, %d inserted", mach, len(events), inserted)
    return inserted


def collect_all(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    opencode_db_path: str = DEFAULT_OPENCODE_DB,
    brain_dir: str = DEFAULT_ANTIGRAVITY_BRAIN_DIR,
    claude_dir: str = DEFAULT_CLAUDE_DIR,
    openclaw_dir: str = DEFAULT_OPENCLAW_DIR
) -> Dict[str, int]:
    """
    Runs all collectors (OpenCode, Antigravity, Claude Code, OpenClaw) and returns summary.
    """
    mach = machine_name or get_default_machine()
    oc = collect_opencode(machine_name=mach, target_db_path=target_db_path, opencode_db_path=opencode_db_path)
    ag = collect_antigravity(machine_name=mach, target_db_path=target_db_path, brain_dir=brain_dir)
    cl = collect_claude(machine_name=mach, target_db_path=target_db_path, claude_dir=claude_dir)
    ow = collect_openclaw(machine_name=mach, target_db_path=target_db_path, openclaw_dir=openclaw_dir)
    return {
        "opencode_inserted": oc,
        "antigravity_inserted": ag,
        "claude_inserted": cl,
        "openclaw_inserted": ow,
        "total_inserted": oc + ag + cl + ow
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="WidgetTokens Local Collector")
    parser.add_argument("--machine", default=get_default_machine(), help="Machine name")
    parser.add_argument("--db", default=os.getenv("WIDGETTOKENS_DB", DEFAULT_DB_PATH), help="Target SQLite DB path")

    args = parser.parse_args()
    summary = collect_all(machine_name=args.machine, target_db_path=args.db)
    print(f"Collection complete: {summary}")
