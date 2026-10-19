import json

from hive.aggregation_service import DeltaCandidate, weighted_average
from hive.audit_service import AuditService
from hive.release_service import build_release_bundle, validate_release_bundle
from hive.slot_registry import SlotRegistry
from hive.trust_service import ConfidentialityLevel, SubmissionContext, validate_submission
from hive.__main__ import main as hive_main


def test_rejects_non_positive_trust_score():
    context = SubmissionContext(
        device_id="device-1",
        app_instance_id="app-1",
        trust_score=0,
        level=ConfidentialityLevel.OFFEN,
    )

    ok, reason = validate_submission(context)
    assert ok is False
    assert "trust_score" in reason


def test_rejects_local_only_submission_for_network_transport():
    context = SubmissionContext(
        device_id="device-2",
        app_instance_id="app-2",
        trust_score=0.8,
        level=ConfidentialityLevel.NUR_LOKAL,
        source="network",
    )

    ok, reason = validate_submission(context)
    assert ok is False
    assert "NUR_LOKAL" in reason


def test_weighted_average_accepts_valid_candidates_only():
    candidates = [
        DeltaCandidate("d1", "a1", 0.6, ConfidentialityLevel.OFFEN, 10.0),
        DeltaCandidate("d2", "a2", 0.4, ConfidentialityLevel.VERTRAULICH, 14.0),
        DeltaCandidate("d3", "a3", 0.9, ConfidentialityLevel.STRENG_GEHEIM, 99.0),
    ]

    result = weighted_average(candidates)
    assert abs(result - 11.6) < 1e-9


def test_strict_secret_candidates_are_filtered_out():
    candidates = [
        DeltaCandidate("d1", "a1", 0.8, ConfidentialityLevel.STRENG_GEHEIM, 100.0),
    ]

    try:
        weighted_average(candidates)
        assert False, "strict-secret candidate should not be aggregated"
    except ValueError:
        pass


def test_release_bundle_validation_accepts_signed_bundle():
    manifest = "version=1.0.0\nartifacts=adapter.gguf"
    bundle = build_release_bundle("1.0.0", manifest, ["adapter.gguf"])

    ok, reason = validate_release_bundle(bundle, manifest)
    assert ok is True
    assert reason == "accepted"


def test_release_bundle_rejects_hash_mismatch():
    bundle = build_release_bundle("1.0.0", "manifest", ["adapter.gguf"])
    tampered = bundle.__class__(version=bundle.version, manifest_hash="deadbeef", signature=bundle.signature, artifacts=bundle.artifacts)

    ok, reason = validate_release_bundle(tampered, "manifest")
    assert ok is False
    assert "hash" in reason


def test_release_bundle_rejects_missing_signature():
    bundle = build_release_bundle("1.0.0", "manifest", ["adapter.gguf"]).__class__(
        version="1.0.0",
        manifest_hash="",
        signature="",
        artifacts=("adapter.gguf",),
    )

    ok, reason = validate_release_bundle(bundle, "manifest")
    assert ok is False
    assert "signature" in reason


def test_audit_service_logs_entries():
    audit = AuditService()

    entry = audit.log("router", "reject", "unknown slot")

    assert entry.actor == "router"
    assert entry.action == "reject"
    assert entry.detail == "unknown slot"
    assert len(audit.entries()) == 1


def test_hive_main_entrypoint_starts_server(monkeypatch):
    called = {}

    class DummyServer:
        def __init__(self, addr, handler):
            called["addr"] = addr

        def serve_forever(self):
            called["started"] = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("hive.__main__.socketserver.TCPServer", DummyServer)
    monkeypatch.setattr("sys.argv", ["hive", "--port", "50051"])

    hive_main()

    assert called["started"] is True
    assert called["addr"] == ("127.0.0.1", 50051)


def test_slot_registry_resolves_active_slots_deterministically():
    registry = SlotRegistry()

    resolved = registry.resolve([" legal ", "finance", "legal", " "])

    assert resolved == ["finance", "legal"]


def test_slot_registry_rejects_unknown_or_inactive_slots():
    registry = SlotRegistry()

    resolved = registry.resolve(["medical", "unknown"])

    assert resolved == []


def test_slot_registry_blocks_local_only_slots():
    registry = SlotRegistry()

    allowed = registry.is_allowed_for_level("legal", ConfidentialityLevel.NUR_LOKAL)

    assert allowed is False


def test_hive_submit_accepts_valid_payload(monkeypatch):
    from hive.__main__ import HiveRequestHandler

    handler = HiveRequestHandler.__new__(HiveRequestHandler)
    handler.path = "/submit"
    handler.headers = {"Content-Length": "118"}
    handler.rfile = type("R", (), {"read": lambda self, n: b'{"device_id":"d1","app_instance_id":"a1","trust_score":0.8,"level":"OFFEN","slots":["legal","finance"],"source":"cloud"}'})()
    responses = []
    monkeypatch.setattr(handler, "_send_json", lambda status, payload: responses.append((status, payload)))

    handler.do_POST()

    assert responses[0][0] == 200
    assert responses[0][1]["accepted"] is True


def test_hive_submit_rejects_invalid_trust(monkeypatch):
    from hive.__main__ import HiveRequestHandler

    handler = HiveRequestHandler.__new__(HiveRequestHandler)
    handler.path = "/submit"
    handler.headers = {"Content-Length": "118"}
    handler.rfile = type("R", (), {"read": lambda self, n: b'{"device_id":"d1","app_instance_id":"a1","trust_score":0,"level":"OFFEN","slots":["legal"],"source":"cloud"}'})()
    responses = []
    monkeypatch.setattr(handler, "_send_json", lambda status, payload: responses.append((status, payload)))

    handler.do_POST()

    assert responses[0][0] == 400
    assert responses[0][1]["accepted"] is False


def test_hive_aggregate_accepts_valid_candidates(monkeypatch):
    from hive.__main__ import HiveRequestHandler

    handler = HiveRequestHandler.__new__(HiveRequestHandler)
    handler.path = "/aggregate"
    handler.headers = {"Content-Length": "118"}
    handler.rfile = type("R", (), {"read": lambda self, n: b'{"candidates":[{"device_id":"d1","app_instance_id":"a1","trust_score":0.8,"level":"OFFEN","value":10.0}]}'})()
    responses = []
    monkeypatch.setattr(handler, "_send_json", lambda status, payload: responses.append((status, payload)))

    handler.do_POST()

    assert responses[0][0] == 200
    assert "weighted_average" in responses[0][1]


def test_feedback_with_evidence_is_accepted():
    from hive.feedback_service import EvidenceRef, FeedbackEvent, validate_feedback

    event = FeedbackEvent(
        event_id="evt-1",
        app_instance_id="app-1",
        model_id="model-1",
        rating=1,
        comment="Hilfreich",
        level=ConfidentialityLevel.OFFEN,
        evidence=(EvidenceRef("src-1", "Quelle A"),),
    )

    ok, reason = validate_feedback(event)
    assert ok is True
    assert reason == "accepted"


def test_feedback_without_evidence_is_rejected_when_rated():
    from hive.feedback_service import FeedbackEvent, validate_feedback

    event = FeedbackEvent(
        event_id="evt-2",
        app_instance_id="app-1",
        model_id="model-1",
        rating=-1,
        comment="Falsch",
        level=ConfidentialityLevel.OFFEN,
    )

    ok, reason = validate_feedback(event)
    assert ok is False
    assert "evidence" in reason


def test_feedback_with_local_only_level_is_rejected():
    from hive.feedback_service import FeedbackEvent, validate_feedback

    event = FeedbackEvent(
        event_id="evt-3",
        app_instance_id="app-1",
        model_id="model-1",
        rating=0,
        comment="Notiz",
        level=ConfidentialityLevel.NUR_LOKAL,
    )

    ok, reason = validate_feedback(event)
    assert ok is False
    assert "NUR_LOKAL" in reason


def test_feedback_with_invalid_rating_is_rejected():
    from hive.feedback_service import FeedbackEvent, validate_feedback

    event = FeedbackEvent(
        event_id="evt-4",
        app_instance_id="app-1",
        model_id="model-1",
        rating=5,
        comment="Ungültig",
        level=ConfidentialityLevel.OFFEN,
    )

    ok, _ = validate_feedback(event)
    assert ok is False


def test_hive_feedback_endpoint_accepts_valid_payload(monkeypatch):
    from hive.__main__ import HiveRequestHandler

    handler = HiveRequestHandler.__new__(HiveRequestHandler)
    handler.path = "/feedback"
    handler.headers = {"Content-Length": "118"}
    handler.rfile = type("R", (), {"read": lambda self, n: b'{"event_id":"e1","app_instance_id":"a1","model_id":"m1","rating":1,"comment":"ok","level":"OFFEN","evidence":[{"source_id":"s1","citation":"Q1"}]}'})()
    responses = []
    monkeypatch.setattr(handler, "_send_json", lambda status, payload: responses.append((status, payload)))

    handler.do_POST()

    assert responses[0][0] == 200
    assert responses[0][1]["accepted"] is True


def test_hive_feedback_endpoint_rejects_missing_evidence(monkeypatch):
    from hive.__main__ import HiveRequestHandler

    handler = HiveRequestHandler.__new__(HiveRequestHandler)
    handler.path = "/feedback"
    handler.headers = {"Content-Length": "118"}
    handler.rfile = type("R", (), {"read": lambda self, n: b'{"event_id":"e2","app_instance_id":"a1","model_id":"m1","rating":1,"comment":"ok","level":"OFFEN","evidence":[]}'})()
    responses = []
    monkeypatch.setattr(handler, "_send_json", lambda status, payload: responses.append((status, payload)))

    handler.do_POST()

    assert responses[0][0] == 400
    assert responses[0][1]["accepted"] is False


def test_hive_release_endpoint_accepts_valid_bundle(monkeypatch):
    from hive.__main__ import HiveRequestHandler

    manifest = "version=1.1.0\nartifacts=adapter.gguf"
    bundle = build_release_bundle("1.1.0", manifest, ["adapter.gguf"])
    body = json.dumps(
        {
            "version": bundle.version,
            "manifest": manifest,
            "manifest_hash": bundle.manifest_hash,
            "signature": bundle.signature,
            "artifacts": list(bundle.artifacts),
        }
    ).encode("utf-8")

    handler = HiveRequestHandler.__new__(HiveRequestHandler)
    handler.path = "/release"
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = type("R", (), {"read": lambda self, n: body})()
    responses = []
    monkeypatch.setattr(handler, "_send_json", lambda status, payload: responses.append((status, payload)))

    handler.do_POST()

    assert responses[0][0] == 200
    assert responses[0][1]["accepted"] is True
    assert responses[0][1]["version"] == "1.1.0"


def test_hive_release_endpoint_rejects_hash_mismatch(monkeypatch):
    from hive.__main__ import HiveRequestHandler

    bundle = build_release_bundle("1.1.0", "manifest", ["adapter.gguf"])
    body = json.dumps(
        {
            "version": bundle.version,
            "manifest": "manifest",
            "manifest_hash": "deadbeef",
            "signature": bundle.signature,
            "artifacts": list(bundle.artifacts),
        }
    ).encode("utf-8")

    handler = HiveRequestHandler.__new__(HiveRequestHandler)
    handler.path = "/release"
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = type("R", (), {"read": lambda self, n: body})()
    responses = []
    monkeypatch.setattr(handler, "_send_json", lambda status, payload: responses.append((status, payload)))

    handler.do_POST()

    assert responses[0][0] == 400
    assert responses[0][1]["accepted"] is False
    assert "hash" in responses[0][1]["reason"]

