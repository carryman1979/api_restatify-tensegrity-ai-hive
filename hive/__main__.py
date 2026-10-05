from __future__ import annotations

import argparse
import json
import http.server
import socketserver
from typing import Any

from hive.aggregation_service import DeltaCandidate, weighted_average
from hive.slot_registry import SlotRegistry
from hive.trust_service import ConfidentialityLevel, SubmissionContext, validate_submission


class HiveRequestHandler(http.server.BaseHTTPRequestHandler):
    registry = SlotRegistry()

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path == "/submit":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8")) if raw else {}
            context = SubmissionContext(
                device_id=data.get("device_id", ""),
                app_instance_id=data.get("app_instance_id", ""),
                trust_score=float(data.get("trust_score", 0.0)),
                level=ConfidentialityLevel[data.get("level", "OFFEN")],
                source=data.get("source", "device"),
            )
            ok, reason = validate_submission(context)
            if not ok:
                self._send_json(400, {"accepted": False, "reason": reason})
                return

            slots = self.registry.resolve(data.get("slots", []))
            self._send_json(
                200,
                {
                    "accepted": True,
                    "resolved_slots": slots,
                    "trust_score": context.trust_score,
                },
            )
            return

        if self.path == "/aggregate":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8")) if raw else {}
            candidates = data.get("candidates", [])
            deltas = []
            for item in candidates:
                deltas.append(
                    DeltaCandidate(
                        device_id=item.get("device_id", ""),
                        app_instance_id=item.get("app_instance_id", ""),
                        trust_score=float(item.get("trust_score", 0.0)),
                        level=ConfidentialityLevel[item.get("level", "OFFEN")],
                        value=float(item.get("value", 0.0)),
                    )
                )

            try:
                value = weighted_average(deltas)
            except ValueError as exc:
                self._send_json(400, {"accepted": False, "reason": str(exc)})
                return

            self._send_json(200, {"accepted": True, "weighted_average": value})
            return

        self._send_json(404, {"error": "not found"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=50051)
    args = parser.parse_args()

    with socketserver.TCPServer(("127.0.0.1", args.port), HiveRequestHandler) as httpd:
        print(f"Hive listening on 127.0.0.1:{args.port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
