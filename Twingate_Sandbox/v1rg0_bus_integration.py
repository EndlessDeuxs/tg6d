# v1rg0_bus_integration.py
# Bus integration layer for the V1rG0 pipeline.
# Publishes proposals to the event bus. Injectable adapter.
# Private logic written first per C_R_ITIC inversion directive.

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ENUMS + RESULT TYPES — private data contracts first
# ---------------------------------------------------------------------------

class BusPublishStatus(str, Enum):
    SUCCESS  = "SUCCESS"
    FAILED   = "FAILED"
    REJECTED = "REJECTED"
    STUB     = "STUB"


@dataclass
class BusPublishResult:
    proposal_id:  str
    topic:        str
    status:       BusPublishStatus
    attempt_count: int
    published_at: Optional[float]  = None
    elapsed_ms:   float            = 0.0
    notes:        List[str]        = field(default_factory=list)
    error:        Optional[str]    = None


# ---------------------------------------------------------------------------
# PRIVATE — adapter call + topic resolution
# ---------------------------------------------------------------------------

def _resolve_topic(proposal: Dict[str, Any]) -> str:
    """
    Maps proposal_type to a bus topic string.

    Convention: v1rg0.proposals.<proposal_type>
    Unknown types fall back to v1rg0.proposals.unclassified.
    """
    proposal_type = proposal.get("proposal_type", "unclassified")
    known_types = {
        "surface_action",
        "hold_action",
        "escalate_action",
        "fallback_action",
        "bypass_action",
        "no_op",
    }
    if proposal_type not in known_types:
        log.warning(
            f"BUS | unknown proposal_type={proposal_type} | "
            f"routing to unclassified topic"
        )
        proposal_type = "unclassified"
    return f"v1rg0.proposals.{proposal_type}"


def _make_bus_call(
    adapter:  Callable[[str, Dict[str, Any]], Dict[str, Any]],
    topic:    str,
    proposal: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Private adapter invocation. Returns normalized result dict.

    Expected adapter signature: adapter(topic, payload) -> {"ok": bool, ...}
    If adapter raises, the exception is caught and surfaced as ok=False.
    """
    try:
        result = adapter(topic, proposal)
        if not isinstance(result, dict):
            return {"ok": False, "error": "adapter returned non-dict"}
        return result
    except Exception as exc:
        log.error(f"BUS ADAPTER EXCEPTION | topic={topic} | error={exc}")
        return {"ok": False, "error": str(exc)}


def _build_success_result(
    proposal_id: str,
    topic:       str,
    attempt:     int,
    t_start:     float,
) -> BusPublishResult:
    elapsed = (time.time() - t_start) * 1000
    return BusPublishResult(
        proposal_id   = proposal_id,
        topic         = topic,
        status        = BusPublishStatus.SUCCESS,
        attempt_count = attempt,
        published_at  = time.time(),
        elapsed_ms    = elapsed,
        notes         = [f"Published on attempt {attempt}."],
    )


def _build_failed_result(
    proposal_id: str,
    topic:       str,
    attempt:     int,
    t_start:     float,
    error:       str,
) -> BusPublishResult:
    elapsed = (time.time() - t_start) * 1000
    return BusPublishResult(
        proposal_id   = proposal_id,
        topic         = topic,
        status        = BusPublishStatus.FAILED,
        attempt_count = attempt,
        elapsed_ms    = elapsed,
        error         = error,
        notes         = [f"Failed after {attempt} attempt(s). Error: {error}"],
    )


def _build_stub_result(
    proposal_id: str,
    topic:       str,
) -> BusPublishResult:
    """
    Stub result. Used when no real adapter is injected.
    Logs and returns success — allows pipeline to continue in dev/test.
    """
    log.info(
        f"BUS STUB | proposal={proposal_id} | topic={topic} | "
        f"no real adapter — stub publish logged"
    )
    return BusPublishResult(
        proposal_id   = proposal_id,
        topic         = topic,
        status        = BusPublishStatus.STUB,
        attempt_count = 1,
        published_at  = time.time(),
        elapsed_ms    = 0.0,
        notes         = ["Stub adapter — no real bus connection."],
    )


# ---------------------------------------------------------------------------
# BUS INTEGRATION — public interface
# ---------------------------------------------------------------------------

class V1rG0BusIntegration:
    """
    Publishes V1rG0 proposals to the event bus.

    Injection pattern:
        bus = V1rG0BusIntegration(adapter=my_real_adapter)

    Stub pattern (dev/test — no real bus):
        bus = V1rG0BusIntegration()

    The Orchestrator calls:
        result = bus.publish(proposal)

    Push dynamic: publish() retries up to max_attempts.
    Pull dynamic: if all attempts fail, returns FAILED for
                  Orchestrator-level compensation.
    """

    def __init__(
        self,
        adapter:      Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
        max_attempts: int = 3,
    ) -> None:
        self._adapter      = adapter
        self._max_attempts = max_attempts

    def publish(
        self,
        proposal: Dict[str, Any],
        notes:    Optional[List[str]] = None,
    ) -> BusPublishResult:
        """
        Publishes a proposal to the bus topic resolved from proposal_type.

        Retries up to max_attempts. Returns BusPublishResult with status
        SUCCESS, FAILED, or STUB.

        STUB is returned when no adapter is injected — safe for dev/test.
        """
        proposal_id = proposal.get("proposal_id", str(uuid.uuid4()))
        topic       = _resolve_topic(proposal)
        t_start     = time.time()

        if self._adapter is None:
            return _build_stub_result(proposal_id, topic)

        attempt    = 0
        last_error = ""

        while attempt < self._max_attempts:
            attempt += 1
            result = _make_bus_call(self._adapter, topic, proposal)

            if result.get("ok"):
                log.info(
                    f"BUS PUBLISH OK | proposal={proposal_id} | "
                    f"topic={topic} | attempt={attempt}"
                )
                return _build_success_result(
                    proposal_id, topic, attempt, t_start
                )

            last_error = result.get("error", "adapter returned not-ok")
            log.warning(
                f"BUS PUBLISH FAIL | proposal={proposal_id} | "
                f"topic={topic} | attempt={attempt}/{self._max_attempts} | "
                f"error={last_error}"
            )

        return _build_failed_result(
            proposal_id, topic, attempt, t_start, last_error
        )

    def inject_adapter(
        self,
        adapter: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """
        Injects or replaces the bus adapter at runtime.
        Allows hot-swap without reconstructing the integration object.
        """
        self._adapter = adapter
        log.info("BUS | adapter injected.")

    def health_check(self) -> Dict[str, Any]:
        """
        Returns the current health state of the bus integration.
        """
        return {
            "adapter_present": self._adapter is not None,
            "max_attempts":    self._max_attempts,
            "status":          "ready" if self._adapter else "stub_mode",
        }
