import unittest
import os
import tempfile
import json
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from backend.server import create_server
from backend.core.db import init_db, insert_events, get_connection


class TestServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "server_test.db")
        init_db(self.db_path)

        # Start server on ephemeral port (e.g., port 0)
        self.httpd = create_server(host="127.0.0.1", port=0, db_path=self.db_path)
        self.port = self.httpd.server_address[1]
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()
        time.sleep(0.05)  # brief wait for thread startup

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp_dir.cleanup()

    def test_health_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/health"
        req = Request(url)
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "healthy")

    def test_sync_and_get_tokens(self):
        # 1. Test POST /api/sync
        sync_url = f"http://127.0.0.1:{self.port}/api/sync"
        payload = {
            "machine": "personal",
            "events": [
                {
                    "id": "pers:opencode:101",
                    "machine": "personal",
                    "source": "opencode",
                    "source_record_id": "101",
                    "timestamp": "2026-11-02T12:00:00Z",
                    "date": "2026-11-02",
                    "input_tokens": 5000,
                    "output_tokens": 1000,
                    "cache_tokens": 500,
                    "total_tokens": 6500
                },
                {
                    "id": "pers:antigravity:102",
                    "machine": "personal",
                    "source": "antigravity",
                    "source_record_id": "102",
                    "timestamp": "2026-11-02T13:00:00Z",
                    "date": "2026-11-02",
                    "input_tokens": 2000,
                    "output_tokens": 500,
                    "cache_tokens": 0,
                    "total_tokens": 2500
                }
            ]
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        req = Request(sync_url, data=body_bytes, headers={"Content-Type": "application/json"})
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_data.get("status"), "ok")
            self.assertEqual(res_data.get("inserted"), 2)

        # 2. Test GET /api/tokens
        tokens_url = f"http://127.0.0.1:{self.port}/api/tokens?days=7&end_date=2026-11-02"
        with urlopen(tokens_url) as resp:
            self.assertEqual(resp.status, 200)
            matrix = json.loads(resp.read().decode("utf-8"))
            self.assertIn("summary", matrix)
            self.assertIn("days", matrix)
            summary = matrix["summary"]
            self.assertEqual(summary["total_tokens"], 9000)
            self.assertEqual(summary["by_machine"]["personal"], 9000)
            self.assertEqual(summary["by_source"]["opencode"], 6500)
            self.assertEqual(summary["by_source"]["antigravity"], 2500)


if __name__ == "__main__":
    unittest.main()
