import unittest
import os
import tempfile
import json
import sqlite3
import threading
import time

from backend.server import create_server
from backend.core.db import init_db, insert_events, get_aggregated_matrix, get_state
from backend.collector import collect_all
from backend.syncer import sync_cycle, DEFAULT_CACHE_PATH


class TestCollectorAndSyncer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client_db = os.path.join(self.temp_dir.name, "client.db")
        self.server_db = os.path.join(self.temp_dir.name, "server.db")
        self.cache_file = os.path.join(self.temp_dir.name, "history.json")

        init_db(self.client_db)
        init_db(self.server_db)

        # Start a mock server for testing
        self.httpd = create_server(host="127.0.0.1", port=0, db_path=self.server_db)
        self.port = self.httpd.server_address[1]
        self.server_url = f"http://127.0.0.1:{self.port}"
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp_dir.cleanup()

    def test_sync_cycle_online(self):
        # Insert a local event in client DB
        client_event = {
            "id": "pers:opencode:test1",
            "machine": "personal",
            "source": "opencode",
            "source_record_id": "test1",
            "timestamp": "2026-11-02T10:00:00Z",
            "date": "2026-11-02",
            "input_tokens": 1000,
            "output_tokens": 200,
            "cache_tokens": 0,
            "total_tokens": 1200
        }
        insert_events([client_event], self.client_db)

        # Run sync cycle (skip real local collection so test is hermetic)
        success = sync_cycle(
            server_url=self.server_url,
            client_db_path=self.client_db,
            cache_file_path=self.cache_file,
            machine_name="personal",
            skip_collection=True
        )
        self.assertTrue(success)

        # Verify that cache_file exists and has 365-day matrix
        self.assertTrue(os.path.exists(self.cache_file))
        with open(self.cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("summary", data)
        self.assertIn("days", data)
        self.assertEqual(data["summary"]["total_tokens"], 1200)

        # Verify server received the event
        matrix = get_aggregated_matrix(days=7, end_date="2026-11-02", db_path=self.server_db)
        self.assertEqual(matrix["summary"]["total_tokens"], 1200)

    def test_sync_cycle_offline_preserves_cache(self):
        # Pre-seed cache file
        seed_data = {"summary": {"total_tokens": 99999}, "days": []}
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(seed_data, f)

        # Sync to a non-existent port (offline)
        offline_url = "http://127.0.0.1:54321"
        success = sync_cycle(
            server_url=offline_url,
            client_db_path=self.client_db,
            cache_file_path=self.cache_file,
            machine_name="personal",
            skip_collection=True
        )
        self.assertFalse(success)

        # Verify cache file is preserved intact
        with open(self.cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["summary"]["total_tokens"], 99999)


if __name__ == "__main__":
    unittest.main()
