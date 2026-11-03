import unittest
import os
import tempfile
import sqlite3
import json
from datetime import datetime, timezone, timedelta

from backend.core.db import (
    init_db,
    insert_events,
    get_events_delta,
    get_aggregated_matrix,
    get_state,
    set_state,
)
from backend.core.extractor import (
    extract_opencode_events,
    extract_antigravity_events,
    generate_event_id,
)


class TestDatabaseAndExtractor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "tokens_test.db")
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_and_state(self):
        set_state("test_key", "12345", self.db_path)
        self.assertEqual(get_state("test_key", self.db_path), "12345")
        self.assertIsNone(get_state("non_existent", self.db_path))

    def test_insert_events_idempotence(self):
        sample_event = {
            "id": "work:opencode:msg_001",
            "machine": "work",
            "source": "opencode",
            "source_record_id": "msg_001",
            "timestamp": "2026-11-01T12:00:00Z",
            "date": "2026-11-01",
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_tokens": 20,
            "total_tokens": 170,
            "raw_json": "{}",
        }
        # Insert once
        count1 = insert_events([sample_event], self.db_path)
        self.assertEqual(count1, 1)

        # Insert again with same ID (should be ignored)
        count2 = insert_events([sample_event], self.db_path)
        self.assertEqual(count2, 0)

        # Verify record in DB
        deltas = get_events_delta(since_timestamp="2026-11-01T00:00:00Z", db_path=self.db_path)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0]["id"], "work:opencode:msg_001")
        self.assertEqual(deltas[0]["total_tokens"], 170)

    def test_aggregated_matrix(self):
        events = [
            {
                "id": "work:opencode:1",
                "machine": "work",
                "source": "opencode",
                "source_record_id": "1",
                "timestamp": "2026-11-01T10:00:00Z",
                "date": "2026-11-01",
                "input_tokens": 1000,
                "output_tokens": 200,
                "cache_tokens": 0,
                "total_tokens": 1200,
            },
            {
                "id": "work:antigravity:2",
                "machine": "work",
                "source": "antigravity",
                "source_record_id": "2",
                "timestamp": "2026-11-01T11:00:00Z",
                "date": "2026-11-01",
                "input_tokens": 500,
                "output_tokens": 100,
                "cache_tokens": 50,
                "total_tokens": 650,
            },
            {
                "id": "personal:opencode:3",
                "machine": "personal",
                "source": "opencode",
                "source_record_id": "3",
                "timestamp": "2026-11-02T15:00:00Z",
                "date": "2026-11-02",
                "input_tokens": 3000,
                "output_tokens": 500,
                "cache_tokens": 0,
                "total_tokens": 3500,
            },
        ]
        insert_events(events, self.db_path)

        matrix_res = get_aggregated_matrix(
            days=7,
            end_date="2026-11-02",
            db_path=self.db_path
        )
        self.assertIn("days", matrix_res)
        self.assertIn("summary", matrix_res)
        self.assertEqual(len(matrix_res["days"]), 7)

        # Day 2026-11-01: total 1850 tokens (work: 1850, personal: 0; opencode: 1200, antigravity: 650)
        day_nov_1 = next(d for d in matrix_res["days"] if d["date"] == "2026-11-01")
        self.assertEqual(day_nov_1["total_tokens"], 1850)
        self.assertEqual(day_nov_1["by_machine"]["work"], 1850)
        self.assertEqual(day_nov_1["by_machine"]["personal"], 0)
        self.assertEqual(day_nov_1["by_source"]["opencode"], 1200)
        self.assertEqual(day_nov_1["by_source"]["antigravity"], 650)

        # Day 2026-11-02: total 3500 tokens (work: 0, personal: 3500)
        day_nov_2 = next(d for d in matrix_res["days"] if d["date"] == "2026-11-02")
        self.assertEqual(day_nov_2["total_tokens"], 3500)
        self.assertEqual(day_nov_2["by_machine"]["personal"], 3500)
        self.assertGreater(day_nov_2["intensity"], 0)

    def test_extract_opencode(self):
        # Create a mock OpenCode SQLite db
        opencode_db_path = os.path.join(self.temp_dir.name, "mock_opencode.db")
        conn = sqlite3.connect(opencode_db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE message (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                time_created INTEGER,
                time_updated INTEGER,
                data TEXT
            )
        """)
        msg1_data = {
            "role": "assistant",
            "tokens": {
                "total": 1250,
                "input": 1000,
                "output": 200,
                "cache": {"read": 50, "write": 0}
            },
            "time": {"created": 1777607758000}
        }
        msg2_user = {
            "role": "user",
            "time": {"created": 1777607750000}
        }
        cur.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
            ("msg_01", "sess_1", 1777607758000, 1777607758000, json.dumps(msg1_data))
        )
        cur.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
            ("msg_02", "sess_1", 1777607750000, 1777607750000, json.dumps(msg2_user))
        )
        conn.commit()
        conn.close()

        extracted = list(extract_opencode_events(
            db_path=opencode_db_path,
            machine_name="personal",
            since_time_created=0
        ))
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["machine"], "personal")
        self.assertEqual(extracted[0]["source"], "opencode")
        self.assertEqual(extracted[0]["total_tokens"], 1250)
        self.assertEqual(extracted[0]["input_tokens"], 1000)
        self.assertEqual(extracted[0]["output_tokens"], 200)
        self.assertEqual(extracted[0]["cache_tokens"], 50)

    def test_extract_antigravity(self):
        # Create a mock brain transcript structure
        brain_dir = os.path.join(self.temp_dir.name, "brain")
        log_dir = os.path.join(brain_dir, "test_session_1", ".system_generated", "logs")
        os.makedirs(log_dir, exist_ok=True)
        transcript_file = os.path.join(log_dir, "transcript.jsonl")

        lines = [
            json.dumps({"type": "USER_INPUT", "created_at": "2026-11-02T10:00:00Z"}),
            json.dumps({
                "type": "PLANNER_RESPONSE",
                "step_index": 1,
                "created_at": "2026-11-02T10:01:00Z",
                "input_tokens": 4000,
                "output_tokens": 300,
                "cache_read_tokens": 150
            }),
            json.dumps({
                "type": "PLANNER_RESPONSE",
                "step_index": 2,
                "created_at": "2026-11-02T10:02:00Z",
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0
            })
        ]
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        extracted = list(extract_antigravity_events(
            brain_dir=brain_dir,
            machine_name="work"
        ))
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["machine"], "work")
        self.assertEqual(extracted[0]["source"], "antigravity")
        self.assertEqual(extracted[0]["input_tokens"], 4000)
        self.assertEqual(extracted[0]["output_tokens"], 300)
        self.assertEqual(extracted[0]["cache_tokens"], 150)
        self.assertEqual(extracted[0]["total_tokens"], 4450)


if __name__ == "__main__":
    unittest.main()
