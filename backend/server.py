import os
import sys
import json
import argparse
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from typing import Optional

from backend.core.db import (
    DEFAULT_DB_PATH,
    init_db,
    insert_events,
    get_aggregated_matrix,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"
)
logger = logging.getLogger("widgettokens.server")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, db_path=None):
        super().__init__(server_address, RequestHandlerClass)
        self.db_path = db_path or DEFAULT_DB_PATH


class TokenRequestHandler(BaseHTTPRequestHandler):
    server: ThreadedHTTPServer

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/health", "/api/health"):
            self._send_json(200, {
                "status": "healthy",
                "service": "widgettokens-server",
                "db_path": self.server.db_path
            })
            return

        if path == "/api/tokens":
            try:
                days_param = int(query.get("days", [365])[0])
            except ValueError:
                days_param = 365

            end_date_param = query.get("end_date", [None])[0]

            try:
                matrix = get_aggregated_matrix(
                    days=days_param,
                    end_date=end_date_param,
                    db_path=self.server.db_path
                )
                self._send_json(200, matrix)
            except Exception as e:
                logger.error("Error generating tokens matrix: %s", e)
                self._send_json(500, {"status": "error", "message": str(e)})
            return

        self._send_json(404, {"status": "error", "message": "Not Found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/sync":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len <= 0:
                    self._send_json(400, {"status": "error", "message": "Empty body"})
                    return

                raw_body = self.rfile.read(content_len)
                data = json.loads(raw_body.decode("utf-8"))

                events = data.get("events", [])
                machine = data.get("machine", "unknown")

                if not isinstance(events, list):
                    self._send_json(400, {"status": "error", "message": "'events' must be an array"})
                    return

                inserted = insert_events(events, db_path=self.server.db_path)
                logger.info(
                    "Sync received from [%s]: %d events received, %d newly inserted",
                    machine, len(events), inserted
                )

                self._send_json(200, {
                    "status": "ok",
                    "machine": machine,
                    "total_received": len(events),
                    "inserted": inserted
                })
            except json.JSONDecodeError:
                self._send_json(400, {"status": "error", "message": "Invalid JSON"})
            except Exception as e:
                logger.error("Error processing sync POST: %s", e)
                self._send_json(500, {"status": "error", "message": str(e)})
            return

        self._send_json(404, {"status": "error", "message": "Not Found"})

    def log_message(self, format, *args):
        # Override standard noisy log to use python logging
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


def create_server(host: str = "0.0.0.0", port: int = 8765, db_path: Optional[str] = None) -> ThreadedHTTPServer:
    init_db(db_path)
    return ThreadedHTTPServer((host, port), TokenRequestHandler, db_path=db_path)


def run_server(host: str = "0.0.0.0", port: int = 8765, db_path: Optional[str] = None):
    server = create_server(host=host, port=port, db_path=db_path)
    logger.info("WidgetTokens Server listening on %s:%d (DB: %s)", host, port, server.db_path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping WidgetTokens Server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WidgetTokens Central Server (Tailscale)")
    parser.add_argument("--host", default=os.getenv("WIDGETTOKENS_HOST", "0.0.0.0"), help="Host address (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.getenv("WIDGETTOKENS_PORT", "8765")), help="Port (default 8765)")
    parser.add_argument("--db", default=os.getenv("WIDGETTOKENS_DB", DEFAULT_DB_PATH), help="Path to SQLite database")

    args = parser.parse_args()
    run_server(host=args.host, port=args.port, db_path=args.db)
