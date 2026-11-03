import os
import sys
import json
import socket
import argparse
import logging
from typing import Dict, Any, Optional

from backend.core.db import (
    DEFAULT_DB_PATH,
    init_db,
    insert_events,
    get_aggregated_matrix,
    get_state,
    set_state,
)
from backend.core.extractor import (
    DEFAULT_OPENCODE_DB,
    DEFAULT_ANTIGRAVITY_BRAIN_DIR,
    DEFAULT_CLAUDE_DIR,
    DEFAULT_OPENCLAW_DIR,
    DEFAULT_HERMES_DB,
    extract_opencode_events,
    extract_antigravity_events,
    extract_claude_events,
    extract_openclaw_events,
    extract_hermes_events,
)

logger = logging.getLogger("widgettokens.collector")

DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/plasma-tokens")
DEFAULT_CACHE_PATH = os.path.join(DEFAULT_CACHE_DIR, "history.json")
DEFAULT_DAYS = 182  # Medio año (~26 semanas)


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


def collect_hermes(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    hermes_db_path: str = DEFAULT_HERMES_DB
) -> int:
    mach = machine_name or get_default_machine()
    init_db(target_db_path)
    state_key = f"{mach}_hermes_last_ts"
    last_ts = get_state(state_key, target_db_path) or ""

    events = []
    max_ts = last_ts
    for ev in extract_hermes_events(db_path=hermes_db_path, machine_name=mach, since_timestamp=last_ts):
        events.append(ev)
        ts = ev.get("timestamp", "")
        if ts > max_ts:
            max_ts = ts

    inserted = insert_events(events, target_db_path)
    if max_ts > last_ts:
        set_state(state_key, max_ts, target_db_path)

    logger.info("Hermes collection [%s]: %d events found, %d inserted", mach, len(events), inserted)
    return inserted


def collect_all(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    opencode_db_path: str = DEFAULT_OPENCODE_DB,
    brain_dir: str = DEFAULT_ANTIGRAVITY_BRAIN_DIR,
    claude_dir: str = DEFAULT_CLAUDE_DIR,
    openclaw_dir: str = DEFAULT_OPENCLAW_DIR,
    hermes_db_path: str = DEFAULT_HERMES_DB
) -> Dict[str, int]:
    """
    Runs all local collectors (OpenCode, Antigravity, Claude Code, OpenClaw, Hermes) and returns summary.
    """
    mach = machine_name or get_default_machine()
    oc = collect_opencode(machine_name=mach, target_db_path=target_db_path, opencode_db_path=opencode_db_path)
    ag = collect_antigravity(machine_name=mach, target_db_path=target_db_path, brain_dir=brain_dir)
    cl = collect_claude(machine_name=mach, target_db_path=target_db_path, claude_dir=claude_dir)
    ow = collect_openclaw(machine_name=mach, target_db_path=target_db_path, openclaw_dir=openclaw_dir)
    hm = collect_hermes(machine_name=mach, target_db_path=target_db_path, hermes_db_path=hermes_db_path)
    return {
        "opencode_inserted": oc,
        "antigravity_inserted": ag,
        "claude_inserted": cl,
        "openclaw_inserted": ow,
        "hermes_inserted": hm,
        "total_inserted": oc + ag + cl + ow + hm
    }


def export_local_history(
    target_db_path: Optional[str] = None,
    cache_file_path: str = DEFAULT_CACHE_PATH,
    days: int = DEFAULT_DAYS
) -> dict:
    """
    Directly builds the aggregated JSON history for the Plasmoid (medio año: 182 días)
    and writes it atomically to the local cache file. No server or network required.
    """
    init_db(target_db_path)
    matrix = get_aggregated_matrix(days=days, db_path=target_db_path)
    os.makedirs(os.path.dirname(os.path.abspath(cache_file_path)), exist_ok=True)
    temp_path = f"{cache_file_path}.tmp.{os.getpid()}"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, cache_file_path)
    logger.info("Exported %d-day local history matrix to %s", days, cache_file_path)
    return matrix


def update_local(
    machine_name: Optional[str] = None,
    target_db_path: Optional[str] = None,
    cache_file_path: str = DEFAULT_CACHE_PATH,
    days: int = DEFAULT_DAYS
) -> dict:
    """
    Full local standalone update cycle:
    1. Collects from all local tools.
    2. Exports aggregated matrix (default 182 days) directly to history.json.
    """
    mach = machine_name or get_default_machine()
    summary = collect_all(machine_name=mach, target_db_path=target_db_path)
    matrix = export_local_history(target_db_path=target_db_path, cache_file_path=cache_file_path, days=days)
    return {
        "collection": summary,
        "matrix_summary": matrix.get("summary", {})
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="WidgetTokens Standalone Local Collector & Exporter")
    parser.add_argument("--machine", default=get_default_machine(), help="Machine name")
    parser.add_argument("--db", default=os.getenv("WIDGETTOKENS_DB", DEFAULT_DB_PATH), help="Target SQLite DB path")
    parser.add_argument("--cache", default=os.getenv("WIDGETTOKENS_CACHE", DEFAULT_CACHE_PATH), help="Plasmoid cache JSON path")
    parser.add_argument("--days", type=int, default=int(os.getenv("WIDGETTOKENS_DAYS", str(DEFAULT_DAYS))), help="Days to aggregate (default: 182, medio año)")
    parser.add_argument("--collect-only", action="store_true", help="Only run collectors without exporting history.json")

    args = parser.parse_args()
    if args.collect_only:
        summary = collect_all(machine_name=args.machine, target_db_path=args.db)
        print(f"Collection complete: {summary}")
    else:
        result = update_local(
            machine_name=args.machine,
            target_db_path=args.db,
            cache_file_path=args.cache,
            days=args.days
        )
        print(f"Local update complete: {result['collection']}")
        print(f"Summary: {result['matrix_summary']}")
