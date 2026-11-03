import os
import glob
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import Iterator, Dict, Any, Optional

DEFAULT_OPENCODE_DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
DEFAULT_ANTIGRAVITY_BRAIN_DIR = os.path.expanduser("~/.gemini/antigravity-cli/brain")
DEFAULT_CLAUDE_DIR = os.path.expanduser("~/.claude")
DEFAULT_OPENCLAW_DIR = os.path.expanduser("~/.openclaw")
DEFAULT_HERMES_DB = os.path.expanduser("~/.hermes/state.db")


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
    Queries the 'message' table for messages created after since_time_created (unix ms).
    """
    if not os.path.exists(db_path):
        return

    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(db_path)

    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
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

            cache_info = tokens_info.get("cache")
            cache_tokens = 0
            if isinstance(cache_info, dict):
                cache_tokens = int(cache_info.get("read") or 0)
            elif isinstance(cache_info, (int, float)):
                cache_tokens = int(cache_info)

            if total_tokens <= 0:
                total_tokens = input_tokens + output_tokens + cache_tokens

            if total_tokens <= 0:
                continue

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

                    if record.get("type") != "PLANNER_RESPONSE":
                        continue

                    iso_ts = record.get("created_at")
                    if not iso_ts:
                        continue

                    if since_timestamp and iso_ts <= since_timestamp:
                        continue

                    inp = int(record.get("input_tokens") or 0)
                    out = int(record.get("output_tokens") or 0)
                    cac = int(record.get("cache_read_tokens") or 0)
                    total = inp + out + cac

                    if total <= 0:
                        continue

                    try:
                        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
                        date_str = dt.strftime("%Y-%m-%d")
                    except Exception:
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


def extract_claude_events(
    claude_dir: str = DEFAULT_CLAUDE_DIR,
    machine_name: str = "personal",
    since_timestamp: Optional[str] = None
) -> Iterator[Dict[str, Any]]:
    """
    Extracts token usage events from Claude Code JSONL transcripts in ~/.claude/projects/*/*.jsonl
    """
    if not os.path.exists(claude_dir):
        return

    pattern = os.path.join(claude_dir, "projects", "*", "*.jsonl")
    jsonl_files = glob.glob(pattern)

    for fpath in jsonl_files:
        filename = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                for line_idx, line in enumerate(fp):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue

                    msg = record.get("message")
                    if not isinstance(msg, dict):
                        continue

                    usage = msg.get("usage")
                    if not isinstance(usage, dict):
                        continue

                    inp = int(usage.get("input_tokens") or 0)
                    out = int(usage.get("output_tokens") or 0)
                    c_read = int(usage.get("cache_read_input_tokens") or 0)
                    c_create = int(usage.get("cache_creation_input_tokens") or 0)
                    cache = c_read + c_create
                    total = inp + out + cache

                    if total <= 0:
                        continue

                    iso_ts = record.get("timestamp")
                    if not iso_ts:
                        continue

                    if since_timestamp and iso_ts <= since_timestamp:
                        continue

                    date_str = iso_ts[:10]
                    record_uid = record.get("uuid") or f"{filename}_{line_idx}_{iso_ts}"
                    event_id = generate_event_id(machine_name, "claude", record_uid)

                    yield {
                        "id": event_id,
                        "machine": machine_name,
                        "source": "claude",
                        "source_record_id": record_uid,
                        "timestamp": iso_ts,
                        "date": date_str,
                        "input_tokens": inp,
                        "output_tokens": out,
                        "cache_tokens": cache,
                        "total_tokens": total,
                        "raw_json": json.dumps({"model": msg.get("model"), "file": filename})
                    }
        except Exception:
            continue


def extract_openclaw_events(
    openclaw_dir: str = DEFAULT_OPENCLAW_DIR,
    machine_name: str = "work",
    since_timestamp: Optional[str] = None
) -> Iterator[Dict[str, Any]]:
    """
    Extracts token usage events from OpenClaw session logs and storage.
    Searches ~/.openclaw/sessions/, ~/.openclaw/agents/*/sessions/, etc.
    """
    if not os.path.exists(openclaw_dir):
        return

    search_patterns = [
        os.path.join(openclaw_dir, "sessions", "*.json"),
        os.path.join(openclaw_dir, "sessions", "*.jsonl"),
        os.path.join(openclaw_dir, "agents", "*", "sessions", "*.json*"),
        os.path.join(openclaw_dir, "logs", "*.json*"),
    ]

    files = []
    for pat in search_patterns:
        files.extend(glob.glob(pat))

    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                # Handle both JSON array / object and JSONL
                content = fp.read().strip()
                if not content:
                    continue

                records = []
                if fpath.endswith(".jsonl"):
                    for l in content.splitlines():
                        if l.strip():
                            try:
                                records.append(json.loads(l))
                            except Exception:
                                pass
                else:
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, list):
                            records = parsed
                        elif isinstance(parsed, dict):
                            records = [parsed]
                    except Exception:
                        pass

                for idx, rec in enumerate(records):
                    # Check various token conventions in OpenClaw
                    usage = rec.get("tokens") or rec.get("usage") or rec.get("token_usage") or {}
                    if not isinstance(usage, dict):
                        continue

                    inp = int(usage.get("input") or usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
                    out = int(usage.get("output") or usage.get("output_tokens") or usage.get("completion_tokens") or 0)
                    cac = int(usage.get("cache") or usage.get("cache_tokens") or 0)
                    tot = int(usage.get("total") or usage.get("total_tokens") or (inp + out + cac))

                    if tot <= 0:
                        continue

                    raw_ts = rec.get("timestamp") or rec.get("created_at") or rec.get("time")
                    if isinstance(raw_ts, (int, float)):
                        # Milliseconds unix
                        dt = datetime.fromtimestamp(raw_ts / 1000.0 if raw_ts > 1e11 else raw_ts, tz=timezone.utc)
                        iso_ts = dt.isoformat()
                        date_str = dt.strftime("%Y-%m-%d")
                    elif isinstance(raw_ts, str):
                        iso_ts = raw_ts
                        date_str = raw_ts[:10]
                    else:
                        mtime = os.path.getmtime(fpath)
                        dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        iso_ts = dt.isoformat()
                        date_str = dt.strftime("%Y-%m-%d")

                    if since_timestamp and iso_ts <= since_timestamp:
                        continue

                    uid = rec.get("id") or f"{fname}_{idx}_{iso_ts}"
                    event_id = generate_event_id(machine_name, "openclaw", uid)

                    yield {
                        "id": event_id,
                        "machine": machine_name,
                        "source": "openclaw",
                        "source_record_id": uid,
                        "timestamp": iso_ts,
                        "date": date_str,
                        "input_tokens": inp,
                        "output_tokens": out,
                        "cache_tokens": cac,
                        "total_tokens": tot,
                        "raw_json": json.dumps({"source_file": fname})
                    }
        except Exception:
            continue


def extract_hermes_events(
    db_path: str = DEFAULT_HERMES_DB,
    machine_name: str = "personal",
    since_timestamp: Optional[str] = None
) -> Iterator[Dict[str, Any]]:
    """
    Extracts token usage events from Hermes agent SQLite database (~/.hermes/state.db).
    Queries the 'sessions' table for token metrics.
    """
    if not os.path.exists(db_path):
        return

    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(db_path)

    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not cur.fetchone():
            return

        query = """
            SELECT id, started_at, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, model
            FROM sessions
            WHERE (input_tokens > 0 OR output_tokens > 0)
            ORDER BY started_at ASC
        """
        for row in cur.execute(query):
            started_at = row["started_at"]
            if not started_at:
                continue

            try:
                ts_val = float(started_at)
                dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                iso_ts = dt.isoformat()
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                continue

            if since_timestamp and iso_ts <= since_timestamp:
                continue

            inp = int(row["input_tokens"] or 0)
            out = int(row["output_tokens"] or 0)
            cache_read = int(row["cache_read_tokens"] or 0)
            cache_write = int(row["cache_write_tokens"] or 0)
            cache = cache_read + cache_write
            tot = inp + out + cache

            if tot <= 0:
                continue

            session_id = str(row["id"])
            event_id = generate_event_id(machine_name, "hermes", session_id)

            yield {
                "id": event_id,
                "machine": machine_name,
                "source": "hermes",
                "source_record_id": session_id,
                "timestamp": iso_ts,
                "date": date_str,
                "input_tokens": inp,
                "output_tokens": out,
                "cache_tokens": cache,
                "total_tokens": tot,
                "raw_json": json.dumps({
                    "model": row["model"] if "model" in row.keys() else None,
                    "session_id": session_id
                })
            }
    except Exception:
        return
    finally:
        conn.close()

