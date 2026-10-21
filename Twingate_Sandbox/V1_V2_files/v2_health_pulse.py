# Twingate_V2/core_logic/v2_health_pulse.py
"""
H.I.G.H.-V2-Pulse health state machine.
States: OK, DEGRADED, WAITING_FOR_PATCH
Dual-channel alerts (primary voice + UDP heartbeat simulation).
State persisted via knowledge store under Conceptual_Core/HIGH_Health_State
"""
from datetime import datetime
from typing import Optional

from Twingate_V2.conceptual_data.v2_conceptual_knowledge_store import V2ConceptualKnowledgeStore


class V2HealthPulse:
    STATES = ["OK", "DEGRADED", "WAITING_FOR_PATCH"]

    def __init__(self, knowledge_store: V2ConceptualKnowledgeStore):
        self.knowledge_store = knowledge_store
        self.state: str = "OK"
        self.consecutive_successes: int = 0
        self._load_state()
        self._emit_alert("H.I.G.H. Pulse initialized")

    def _load_state(self):
        saved = self.knowledge_store.get_concept("Conceptual_Core/HIGH_Health_State") or {}
        if saved:
            self.state = saved.get("state", "OK")
            self.consecutive_successes = saved.get("consecutive_successes", 0)

    def _save_state(self):
        self.knowledge_store.add_concept("Conceptual_Core/HIGH_Health_State", {
            "state": self.state,
            "consecutive_successes": self.consecutive_successes,
            "timestamp": datetime.utcnow().isoformat()
        })

    def _emit_alert(self, message: str, channel: str = "both"):
        ts = datetime.utcnow().isoformat()
        alert = {
            "message": message,
            "state": self.state,
            "timestamp": ts
        }
        if channel in ("primary", "both"):
            print(f"[H.I.G.H. PRIMARY] {message} | state={self.state}")
        if channel in ("udp", "both"):
            print(f"[H.I.G.H. UDP_HEARTBEAT] {message} | state={self.state} | ts={ts}")
        # persist recent alerts
        alerts = self.knowledge_store.get_concept("Conceptual_Core/Health_Alerts") or []
        alerts.append(alert)
        self.knowledge_store.add_concept("Conceptual_Core/Health_Alerts", alerts[-20:])

    def report_success(self):
        self.consecutive_successes += 1
        old_state = self.state
        if self.state == "DEGRADED" and self.consecutive_successes >= 3:
            self.state = "OK"
            self.consecutive_successes = 0
            self._emit_alert("DEGRADED -> OK after 3 consecutive successful API calls")
        elif self.state == "WAITING_FOR_PATCH":
            # ACK or success can recover
            self.state = "OK"
            self.consecutive_successes = 0
            self._emit_alert("WAITING_FOR_PATCH -> OK (success/ACK received)")
        if old_state != self.state:
            self._save_state()
        else:
            self._save_state()

    def report_failure(self):
        old_state = self.state
        if self.state == "OK":
            self.state = "DEGRADED"
            self.consecutive_successes = 0
            self._emit_alert("OK -> DEGRADED (gate failure)")
        self._save_state()
        if old_state != self.state:
            self._emit_alert(f"State transition: {old_state} -> {self.state}")

    def set_waiting_for_patch(self, reason: str = "All gates failed"):
        self.state = "WAITING_FOR_PATCH"
        self.consecutive_successes = 0
        self._emit_alert(f"DEGRADED -> WAITING_FOR_PATCH: {reason}")
        self._save_state()

    def get_state(self) -> str:
        return self.state

    def poll(self):
        """Simulates the 8-second poll. Call periodically in daemon context."""
        print(f"[H.I.G.H. POLL @8s] Current HIGH state: {self.state}")
        # In real impl this would be in a background thread/timer
        return self.state

    def receive_ack(self):
        """Called when V1 ACK arrives."""
        if self.state == "WAITING_FOR_PATCH":
            self.state = "OK"
            self.consecutive_successes = 0
            self._emit_alert("WAITING_FOR_PATCH -> OK via V1 ACK")
            self._save_state()
