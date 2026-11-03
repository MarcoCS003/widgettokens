import os
import glob
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import Iterator, Dict, Any, Optional

DEFAULT_OPENCODE_DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
DEFAULT_ANTIGRAVITY_BRAIN_DIR = os.path.expanduser("~/.gemini/antigravity-cli/brain")


def generate_event_id(machine: str, source: str, record_id: str) -> str:
    raw = f"{machine}:{source}:{record_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def extract_opencode_events(
    db_path: str = DEFAULT_OPENCODE_DB,
    machine_name: str = "personal",
    since_time_created: int = 0
) -> Iterator[Dict[str, Any]]:
    """
    Extracts token usage events from OpenCode's SQLite database.
    Queries the 'message' table for messages created after `since_time_created` (unix ms).
    """
    if not os.path.exists(db_path):
        return

    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        # Fallback to standard connect if URI mode fails
        conn = sqlite3.connect(db_path)

    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Verify table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message'")
        if not cur.fetchone():
            return

        query = """
            SELECT id, time_created, data
            FROM message
            WHERE data IS NOT NULL AND time_created > ?
            ORDER BY time_created ASC
        """
        cur.execute(query, (since_time_created,))

        for row in cur.fetchall():
            msg_id = str(row["id"])
            col_time_created = row["time_created"] or 0
            raw_data = row["data"]
            try:
                data = json.loads(raw_data)
            except Exception:
                continue

            tokens_info = data.get("tokens")
            if not isinstance(tokens_info, dict):
                continue

            total_tokens = int(tokens_info.get("total") or 0)
            input_tokens = int(tokens_info.get("input") or 0)
            output_tokens = int(tokens_info.get("output") or 0)

            # cache can be int or dict {'read': int, 'write': int}
            cache_info = tokens_info.get("cache")
            cache_tokens = 0
            if isinstance(cache_info, dict):
                cache_tokens = int(cache_info.get("read") or 0)
            elif isinstance(cache_info, (int, float)):
                cache_tokens = int(cache_info)

            # If total is 0 but we have input or output, recalculate
            if total_tokens <= 0:
                total_tokens = input_tokens + output_tokens + cache_tokens

            if total_tokens <= 0:
                continue

            # Timestamp extraction: check time.created (ms) in data or fallback to column
            time_dict = data.get("time")
            ms_created = col_time_created
            if isinstance(time_dict, dict) and "created" in time_dict:
                ms_created = int(time_dict["created"])

            if ms_created <= 0:
                continue

            dt = datetime.fromtimestamp(ms_created / 1000.0, tz=timezone.utc)
            iso_ts = dt.isoformat()
            date_str = dt.strftime("%Y-%m-%d")

            event_id = generate_event_id(machine_name, "opencode", msg_id)

            yield {
                "id": event_id,
                "machine": machine_name,
                "source": "opencode",
                "source_record_id": msg_id,
                "timestamp": iso_ts,
                "date": date_str,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_tokens": cache_tokens,
                "total_tokens": total_tokens,
                "raw_json": json.dumps({"ms_created": ms_created, "model": data.get("model")})
            }
    finally:
        conn.close()


def extract_antigravity_events(
    brain_dir: str = DEFAULT_ANTIGRAVITY_BRAIN_DIR,
    machine_name: str = "personal",
    since_timestamp: Optional[str] = None
) -> Iterator[Dict[str, Any]]:
    """
    Extracts token usage events from Antigravity JSONL transcripts.
    Searches brain_dir/*/.system_generated/logs/transcript.jsonl
    """
    if not os.path.exists(brain_dir):
        return

    pattern = os.path.join(brain_dir, "*", ".system_generated", "logs", "transcript.jsonl")
    transcript_files = glob.glob(pattern)

    for fpath in transcript_files:
        # Session directory name as unique context
        parts = fpath.split(os.sep)
        session_id = "unknown"
        if ".system_generated" in parts:
            idx = parts.index(".system_generated")
            if idx > 0:
                session_id = parts[idx - 1]

        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                for line_num, line in enumerate(fp):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue

                    # Filter: PLANNER_RESPONSE
                    if record.get("type") != "PLANNER_RESPONSE":
                        continue

                    iso_ts = record.get("created_at")
                    if not iso_ts:
                        continue

                    # Check since_timestamp filter
                    if since_timestamp and iso_ts <= since_timestamp:
                        continue

                    inp = int(record.get("input_tokens") or 0)
                    out = int(record.get("output_tokens") or 0)
                    cac = int(record.get("cache_read_tokens") or 0)
                    total = inp + out + cac

                    if total <= 0:
                        continue

                    try:
                        # Normalize ISO timestamp and date
                        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
                        date_str = dt.strftime("%Y-%m-%d")
                    except Exception:
                        # Fallback parsing YYYY-MM-DD
                        date_str = iso_ts[:10]

                    step_index = record.get("step_index", line_num)
                    record_uid = f"{session_id}_{step_index}_{iso_ts}"
                    event_id = generate_event_id(machine_name, "antigravity", record_uid)

                    yield {
                        "id": event_id,
                        "machine": machine_name,
                        "source": "antigravity",
                        "source_record_id": record_uid,
                        "timestamp": iso_ts,
                        "date": date_str,
                        "input_tokens": inp,
                        "output_tokens": out,
                        "cache_tokens": cac,
                        "total_tokens": total,
                        "raw_json": json.dumps({"session_id": session_id, "step_index": step_index})
                    }
        except Exception:
            continue
