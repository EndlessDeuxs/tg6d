# api_gateway.py
import json, uuid, hmac, hashlib, time
from datetime import datetime
from pulse import PulseBus, PulseSignal
from contract_registry import ContractRegistry, attach_contract_middleware

# =============================================================================
# V1rG0 COUNCIL PATCHES — extracted from WCR set 2026-07-03 11:08:58
# All the small "tag-on" snippets scattered through council output,
# deduplicated, labeled with source, and sorted IMPLEMENT vs SKIP.
#
# BASE RECOMMENDATION: use ANCH_OR Round 3's APIGateway + AuthSuit as your
# foundation (it's the only round where gateway, auth, and E2E test were
# written as one coherent set), then apply Patches 1-6 below on top of it.
# =============================================================================

import re
import threading
from datetime import datetime

# -----------------------------------------------------------------------------
# PATCH 1 — IMPLEMENT — Response echo loop fix, part A (pop-or-guard)
# Source: C_R_ITIC Round 1, Finding 01
# Fixes: _return_response re-triggering _handle_response via its own
#        api_response emission. Pop from pending BEFORE emitting.
# Requires in __init__:  self._completed_requests: dict[str, dict] = {}
# Note: get_response() must query _completed_requests, not _pending_requests.
# -----------------------------------------------------------------------------
def _return_response(self, request_id: str, status: int, data: dict):
    if request_id not in self._pending_requests:
        return  # Already resolved. Do not re-emit.

    record = self._pending_requests.pop(request_id)  # Remove FIRST
    record["status"] = "completed"
    record["response"] = {"status": status, "data": data}

    self._completed_requests[request_id] = record

    # NOW emit — no longer in pending, loop is broken
    self.pulse_bus.emit(
        self.SUIT_ID,
        "api_response",
        {
            "request_id": request_id,
            "status": status,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        },
    )


# -----------------------------------------------------------------------------
# PATCH 2 — IMPLEMENT — Response echo loop fix, part B (origin guard)
# Source: C_R_ITIC Round 3, Flag 3
# Fixes: gateway subscribing to "api_response" while also emitting it.
# Belt-and-suspenders with Patch 1; costs one line, keep both.
# -----------------------------------------------------------------------------
def _handle_response(self, signal):
    # Do not process our own emissions
    if signal.source_suit == self.SUIT_ID:
        return
    # ... rest of existing handler ...


# -----------------------------------------------------------------------------
# PATCH 3 — IMPLEMENT — /v1/ prefix normalization + 404 fallthrough
# Source: C_R_ITIC Round 1 Finding 04 (normalize) merged with
#         C_R_ITIC Round 3 Flag 2 (explicit fallthrough)
# Fixes: BOTH critical routing bugs at once — versioned routes silently
#        falling through all conditionals, and unmatched endpoints hanging
#        in "processing" forever with no error and no DLQ entry.
# Internal routing stays version-agnostic; versioning is a boundary concern.
# -----------------------------------------------------------------------------
def _normalize_endpoint(self, endpoint: str) -> str:
    return re.sub(r"^/v\d+", "", endpoint)


def _route_internal(self, endpoint: str, request_id: str, payload: dict):
    normalized = self._normalize_endpoint(endpoint)

    if normalized.startswith("/concept"):
        pass  # ... existing transform_concept emit ...
    elif normalized.startswith("/design"):
        pass  # ... existing validate_design emit ...
    elif normalized.startswith("/proposal"):
        pass  # ... existing propose emit ...
    elif normalized.startswith("/health"):
        pass  # ... existing direct health response ...
    # NOTE: /memory intentionally absent — council voted to shelve it this
    # sprint (MemoryStore logs but has no query-response path; routes to void).
    else:
        # Explicit fallthrough — no more silent hangs
        self.pulse_bus.emit(
            self.SUIT_ID,
            "route_error",
            {
                "request_id": request_id,
                "endpoint": endpoint,
                "reason": "no_matching_route",
                "timestamp": datetime.now().isoformat(),
            },
        )
        self._return_response(
            request_id, 404, {"error": "endpoint_not_found", "endpoint": endpoint}
        )


# -----------------------------------------------------------------------------
# PATCH 4 — IMPLEMENT — TTL eviction for completed requests
# Source: C_R_ITIC Round 3, Flag 1 (adapted)
# Fixes: unbounded memory growth. With Patch 1 applied, the leak moves from
#        _pending_requests to _completed_requests, so evict from THERE.
#        Call self._schedule_eviction(request_id, 300) at the end of
#        _return_response.
# -----------------------------------------------------------------------------
def _schedule_eviction(self, request_id: str, ttl_seconds: int = 300):
    """After TTL, drop completed request. Caller must have already
    retrieved the response or accepted the loss."""
    def evict():
        self._completed_requests.pop(request_id, None)
    t = threading.Timer(ttl_seconds, evict)
    t.daemon = True
    t.start()


# -----------------------------------------------------------------------------
# PATCH 5 — IMPLEMENT (this version) — DLQ exponential backoff
# Source: DRIFT_R Round 1  (returns delay in MILLISECONDS, capped 30s)
# The SKIP version: DRIFT_R Round 2 wrote a retry() that calls
# time.sleep(delay) inline — that BLOCKS the whole PulseBus thread for up
# to 30 seconds per retry. Do not use it. Schedule the re-emit with a
# threading.Timer instead, same pattern as Patch 4.
# -----------------------------------------------------------------------------
def _calculate_retry_delay(self, attempt: int) -> int:
    return min((2 ** attempt) * 100, 30000)  # milliseconds, capped at 30s


# -----------------------------------------------------------------------------
# PATCH 6 — IMPLEMENT — Terminal failure mapping (DLQ exhaustion -> caller)
# Source: ANCH_OR Round 3, section 5
# Fixes: caller polling forever when a downstream suit gives up. When DLQ
#        retries exhaust, the failing suit emits a terminal *_error signal
#        and the gateway converts it to a clean 500.
# Wire in __init__:
#   pulse_bus.subscribe("concept_transform_failed", self._handle_concept_error)
# (Repeat the pattern per suit: validation_failed, proposal_failed, etc.)
# -----------------------------------------------------------------------------
def _handle_concept_error(self, signal):
    payload = signal.payload
    request_id = payload.get("request_id")
    if request_id and request_id in self._pending_requests:
        self._return_response(
            request_id,
            500,
            {"error": "concept_transform_failed", "reason": payload.get("reason")},
        )


# =============================================================================
# SKIP LIST — snippets that appear in the logs but should NOT be implemented
# =============================================================================
# - DRIFT_R R3: receive_request that does `raise ValueError("401 Unauthorized")`
#   on auth failure. Raising instead of returning a response crashes the
#   caller's thread instead of answering it. Discard.
# - DRIFT_R R2: AuthSuit validating against self._keys.values() (comparing a
#   submitted key against HASHES of keys — clients would have to send the
#   hash, defeating the purpose). Discard.
# - PLANN_R R1/R2/R3 + SYNTHESIZ_R AuthSuit variants (HMAC signing-string,
#   timestamp replay windows, event-driven auth_success/auth_failure flows):
#   architecturally fine but each is incompatible with the others and all are
#   overkill for sandbox. Keep ONE on file as the future upgrade path
#   (PLANN_R R2's is the most complete); implement NONE of them now.
#   ANCH_OR R3's simple valid_keys dict is the sandbox implementation.
# - CONDENS_OR R3 "self-modification trigger" / dynamic endpoint registration:
#   design idea only, no code exists. Do not let TG6D hallucinate an
#   implementation during compaction — explicitly out of scope.
# - Everything from the 11:15:52 and 11:18:28 WCR sets: those runs derailed
#   (context loss + Claude gate 400s + drift into Twingate-the-company docs).
#   No code from those sets is trustworthy. Extract nothing from them.
# =============================================================================

class AuthSuit:
    SUIT_ID = "auth_suit"
    _keys = {"test_key_001": "test_secret_001"}
    
    @classmethod
    def validate_request(cls, api_key: str, signature: str, payload: str, timestamp: int) -> bool:
        if api_key not in cls._keys:
            return False
        if abs(time.time() - timestamp) > 300:
            return False
        expected = hmac.new(cls._keys[api_key].encode(), f"{timestamp}{payload}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

class APIGateway:
    SUIT_ID = "api_gateway"
    
    def __init__(self, pulse_bus: PulseBus):
        self.pulse_bus = pulse_bus
        self._pending = {}
        ContractRegistry().register_suit(self.SUIT_ID, {
            "input": {"type": "api_request", "required_fields": ["endpoint", "method", "payload"]},
            "output": {"type": "api_response", "required_fields": ["request_id", "status", "data"]}
        })
        attach_contract_middleware(pulse_bus, self.SUIT_ID)
        pulse_bus.subscribe("api_response", self._handle_response)
        pulse_bus.subscribe("design_ready", self._handle_design)
        pulse_bus.subscribe("validation_result", self._handle_validation)
    
    def receive(self, endpoint: str, method: str, payload: dict = None, api_key: str = None, signature: str = None, timestamp: int = 0) -> str:
        rid = str(uuid.uuid4())[:12]
        if api_key and not AuthSuit.validate_request(api_key, signature, json.dumps(payload or {}), timestamp):
            self._return_response(rid, 401, {"error": "unauthorized"})
            return rid
        self._pending[rid] = {"endpoint": endpoint, "method": method, "payload": payload, "timestamp": datetime.now().isoformat(), "status": "processing"}
        self.pulse_bus.emit(self.SUIT_ID, "api_request", {"request_id": rid, "endpoint": endpoint, "method": method, "payload": payload or {}, "timestamp": self._pending[rid]["timestamp"]})
        self._route(endpoint, rid, payload)
        return rid
    
    def _route(self, endpoint: str, rid: str, payload: dict):
        if endpoint == "/v1/health":
            self._return_response(rid, 200, {"status": "healthy", "timestamp": datetime.now().isoformat()})
        elif endpoint == "/v1/concept":
            self.pulse_bus.emit(self.SUIT_ID, "transform_concept", {"request_id": rid, "type": "concept", "concept_id": payload.get("concept_id", f"CON-{rid}"), "description": payload.get("description", ""), "source": "api_gateway"})
        elif endpoint == "/v1/design":
            self.pulse_bus.emit(self.SUIT_ID, "validate_design", {"request_id": rid, "design_id": payload.get("design_id"), "specification": payload.get("specification", {})})
        elif endpoint == "/v1/proposal":
            self.pulse_bus.emit(self.SUIT_ID, "propose", {"request_id": rid, "proposal_id": payload.get("proposal_id"), "signal_id": payload.get("signal_id")})
        elif endpoint == "/v1/memory":
            self.pulse_bus.emit(self.SUIT_ID, "memory_query", {"request_id": rid, "query_params": payload.get("query_params", {}), "limit": payload.get("limit", 10)})
        else:
            self._return_response(rid, 404, {"error": "not_found"})
    
    def _handle_response(self, signal: PulseSignal):
        p = signal.payload
        if p.get("request_id") in self._pending:
            self._return_response(p["request_id"], p.get("status", 200), p.get("data", {}))
    
    def _handle_design(self, signal: PulseSignal):
        p = signal.payload
        if p.get("request_id") in self._pending:
            self._return_response(p["request_id"], 200, {"type": "design", "design_id": p.get("design_id"), "specification": p.get("specification"), "timestamp": p.get("timestamp")})
    
    def _handle_validation(self, signal: PulseSignal):
        p = signal.payload
        if p.get("request_id") in self._pending:
            self._return_response(p["request_id"], 200 if p.get("valid") else 400, {"type": "validation", "design_id": p.get("design_id"), "valid": p.get("valid", False), "issues": p.get("issues", [])})
    
    def _return_response(self, rid: str, status: int, data: dict):
        if rid in self._pending:
            self._pending[rid]["status"] = "completed"
            self._pending[rid]["response"] = {"status": status, "data": data}
            self.pulse_bus.emit(self.SUIT_ID, "api_response", {"request_id": rid, "status": status, "data": data, "timestamp": datetime.now().isoformat()})
    
    def get_response(self, rid: str) -> dict | None:
        return self._pending.get(rid, {}).get("response")
