import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

DEFAULT_DB_DIR = os.path.expanduser("~/.local/share/widgettokens")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "tokens.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_events (
                    id TEXT PRIMARY KEY,
                    machine TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    raw_json TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON token_events(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON token_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_machine ON token_events(machine)")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS collector_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
    finally:
        conn.close()


def insert_events(events: List[Dict[str, Any]], db_path: Optional[str] = None) -> int:
    if not events:
        return 0
    conn = get_connection(db_path)
    inserted = 0
    try:
        with conn:
            for ev in events:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO token_events (
                        id, machine, source, source_record_id, timestamp, date,
                        input_tokens, output_tokens, cache_tokens, total_tokens, raw_json
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    ev["id"],
                    ev["machine"],
                    ev["source"],
                    ev.get("source_record_id", ""),
                    ev["timestamp"],
                    ev["date"],
                    ev.get("input_tokens", 0),
                    ev.get("output_tokens", 0),
                    ev.get("cache_tokens", 0),
                    ev.get("total_tokens", 0),
                    ev.get("raw_json", "")
                ))
                inserted += cur.rowcount
    finally:
        conn.close()
    return inserted


def get_events_delta(
    since_timestamp: Optional[str] = None,
    machine: Optional[str] = None,
    db_path: Optional[str] = None,
    limit: int = 50000
) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM token_events WHERE 1=1"
        params: List[Any] = []
        if since_timestamp:
            query += " AND timestamp > ?"
            params.append(since_timestamp)
        if machine:
            query += " AND machine = ?"
            params.append(machine)
        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        rows = [dict(row) for row in cur.fetchall()]
        return rows
    finally:
        conn.close()


def get_state(key: str, db_path: Optional[str] = None) -> Optional[str]:
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT value FROM collector_state WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_state(key: str, value: str, db_path: Optional[str] = None) -> None:
    conn = get_connection(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            conn.execute("""
                INSERT INTO collector_state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """, (key, value, now_iso))
    finally:
        conn.close()


def get_aggregated_matrix(
    days: int = 365,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns an aggregated daily matrix for the last N days up to end_date (inclusive).
    Includes summary statistics and 4-tier intensity levels for heatmap visualization.
    """
    if end_date is None:
        today = datetime.now(timezone.utc).date()
    else:
        today = datetime.strptime(end_date, "%Y-%m-%d").date()

    start_date = today - timedelta(days=days - 1)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    conn = get_connection(db_path)
    try:
        cur = conn.execute("""
            SELECT
                date,
                machine,
                source,
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(cache_tokens) as total_cache,
                SUM(total_tokens) as total_tokens
            FROM token_events
            WHERE date >= ? AND date <= ?
            GROUP BY date, machine, source
            ORDER BY date ASC
        """, (start_str, end_str))
        rows = cur.fetchall()
    finally:
        conn.close()

    # Organize daily aggregated data
    day_map: Dict[str, Dict[str, Any]] = {}
    curr = start_date
    while curr <= today:
        d_str = curr.strftime("%Y-%m-%d")
        day_map[d_str] = {
            "date": d_str,
            "weekday": curr.weekday(),  # 0: Mon, 6: Sun
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_tokens": 0,
            "by_machine": {},
            "by_source": {},
            "intensity": 0,
        }
        curr += timedelta(days=1)

    summary_by_machine: Dict[str, int] = {}
    summary_by_source: Dict[str, int] = {}

    for r in rows:
        d_str = r["date"]
        if d_str not in day_map:
            continue
        m = r["machine"]
        s = r["source"]
        tot = r["total_tokens"] or 0
        inp = r["total_input"] or 0
        out = r["total_output"] or 0
        cac = r["total_cache"] or 0

        day_data = day_map[d_str]
        day_data["total_tokens"] += tot
        day_data["input_tokens"] += inp
        day_data["output_tokens"] += out
        day_data["cache_tokens"] += cac

        day_data["by_machine"][m] = day_data["by_machine"].get(m, 0) + tot
        day_data["by_source"][s] = day_data["by_source"].get(s, 0) + tot

        summary_by_machine[m] = summary_by_machine.get(m, 0) + tot
        summary_by_source[s] = summary_by_source.get(s, 0) + tot

    all_days = list(day_map.values())

    # Calculate quartiles for intensity scaling (0: none, 1: low, 2: medium, 3: high, 4: very high, 5: epic >100M)
    active_totals = [d["total_tokens"] for d in all_days if d["total_tokens"] > 0]
    active_totals.sort()

    below_100m = [t for t in active_totals if t < 100_000_000]
    q_pool = below_100m if below_100m else active_totals

    q1, q2, q3 = 0, 0, 0
    if q_pool:
        n = len(q_pool)
        q1 = q_pool[n // 4]
        q2 = q_pool[n // 2]
        q3 = q_pool[(3 * n) // 4]

    for d in all_days:
        tot = d["total_tokens"]
        if tot == 0:
            d["intensity"] = 0
        elif tot >= 100_000_000:
            d["intensity"] = 5
        elif tot <= q1 or q1 == q2:
            d["intensity"] = 1
        elif tot <= q2 or q2 == q3:
            d["intensity"] = 2
        elif tot <= q3:
            d["intensity"] = 3
        else:
            d["intensity"] = 4

    grand_total = sum(d["total_tokens"] for d in all_days)
    today_data = day_map.get(end_str, {})
    today_total = today_data.get("total_tokens", 0)

    summary = {
        "range_start": start_str,
        "range_end": end_str,
        "days_count": len(all_days),
        "total_tokens": grand_total,
        "today_tokens": today_total,
        "by_machine": summary_by_machine,
        "by_source": summary_by_source,
        "quantiles": {
            "q1": q1,
            "q2": q2,
            "q3": q3,
            "threshold_epic": 100000000
        }
    }

    return {
        "summary": summary,
        "days": all_days
    }
