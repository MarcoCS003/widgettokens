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
    extract_claude_events,
    extract_openclaw_events,
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
            "machine": "marcoijl",
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
        count1 = insert_events([sample_event], self.db_path)
        self.assertEqual(count1, 1)

        count2 = insert_events([sample_event], self.db_path)
        self.assertEqual(count2, 0)

        deltas = get_events_delta(since_timestamp="2026-11-01T00:00:00Z", db_path=self.db_path)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0]["id"], "work:opencode:msg_001")
        self.assertEqual(deltas[0]["total_tokens"], 170)

    def test_aggregated_matrix_dynamic_machines_and_sources(self):
        events = [
            {
                "id": "ev1",
                "machine": "marcoijl",
                "source": "openclaw",
                "source_record_id": "1",
                "timestamp": "2026-11-01T10:00:00Z",
                "date": "2026-11-01",
                "input_tokens": 1000,
                "output_tokens": 200,
                "cache_tokens": 0,
                "total_tokens": 1200,
            },
            {
                "id": "ev2",
                "machine": "fedora",
                "source": "claude",
                "source_record_id": "2",
                "timestamp": "2026-11-01T11:00:00Z",
                "date": "2026-11-01",
                "input_tokens": 500,
                "output_tokens": 100,
                "cache_tokens": 50,
                "total_tokens": 650,
            },
        ]
        insert_events(events, self.db_path)

        matrix_res = get_aggregated_matrix(
            days=2,
            end_date="2026-11-01",
            db_path=self.db_path
        )
        self.assertIn("days", matrix_res)
        self.assertIn("summary", matrix_res)
        summary = matrix_res["summary"]
        self.assertEqual(summary["total_tokens"], 1850)
        self.assertEqual(summary["by_machine"]["marcoijl"], 1200)
        self.assertEqual(summary["by_machine"]["fedora"], 650)
        self.assertEqual(summary["by_source"]["openclaw"], 1200)
        self.assertEqual(summary["by_source"]["claude"], 650)

    def test_extract_claude_code(self):
        claude_dir = os.path.join(self.temp_dir.name, ".claude")
        proj_dir = os.path.join(claude_dir, "projects", "my-project")
        os.makedirs(proj_dir, exist_ok=True)
        session_file = os.path.join(proj_dir, "session1.jsonl")

        lines = [
            json.dumps({"type": "user", "timestamp": "2026-11-02T10:00:00.000Z"}),
            json.dumps({
                "type": "assistant",
                "uuid": "c-uuid-1",
                "timestamp": "2026-11-02T10:01:00.000Z",
                "message": {
                    "usage": {
                        "input_tokens": 2000,
                        "output_tokens": 400,
                        "cache_read_input_tokens": 1000,
                        "cache_creation_input_tokens": 500
                    }
                }
            })
        ]
        with open(session_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        extracted = list(extract_claude_events(
            claude_dir=claude_dir,
            machine_name="fedora"
        ))
        self.assertEqual(len(extracted), 1)
        ev = extracted[0]
        self.assertEqual(ev["source"], "claude")
        self.assertEqual(ev["machine"], "fedora")
        self.assertEqual(ev["input_tokens"], 2000)
        self.assertEqual(ev["output_tokens"], 400)
        self.assertEqual(ev["cache_tokens"], 1500)
        self.assertEqual(ev["total_tokens"], 3900)

    def test_extract_openclaw(self):
        openclaw_dir = os.path.join(self.temp_dir.name, ".openclaw")
        sessions_dir = os.path.join(openclaw_dir, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        session_file = os.path.join(sessions_dir, "session_001.json")

        sample_claw = [
            {
                "id": "claw-step-1",
                "timestamp": "2026-11-02T12:00:00Z",
                "tokens": {
                    "input": 1500,
                    "output": 350,
                    "cache": 200,
                    "total": 2050
                }
            }
        ]
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(sample_claw, f)

        extracted = list(extract_openclaw_events(
            openclaw_dir=openclaw_dir,
            machine_name="marcoijl"
        ))
        self.assertEqual(len(extracted), 1)
        ev = extracted[0]
        self.assertEqual(ev["source"], "openclaw")
        self.assertEqual(ev["machine"], "marcoijl")
        self.assertEqual(ev["total_tokens"], 2050)
        self.assertEqual(ev["input_tokens"], 1500)
        self.assertEqual(ev["output_tokens"], 350)
        self.assertEqual(ev["cache_tokens"], 200)


if __name__ == "__main__":
    unittest.main()
