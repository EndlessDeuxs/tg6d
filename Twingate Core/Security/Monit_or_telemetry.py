#Security_Subsystem
# FILENAME: Monit.or_telemetry.py
"""
Monit.or Connection Telemetry
Logs routing metadata only — no prompt or payload text.
"""
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

# Bulletproof Pathing: Force Python to recognize the parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) 
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Absolute import bypassing the '..' logic
from InternalRegulations.Twingate_internal_config import LOG_PATHS, SEVERITY_LEVELS, get_severity_tag

ROUTING_LOG_FILE = "Monit_or_Routing_Log.txt"

_STRIP_KEYS = frozenset({
    "content", "prompt", "context", "payload", "text", "message",
    "body", "transcript", "response", "output", "raw", "data",
})

_TRUNCATE_LEN = 0


class MonitorTelemetry:
    def __init__(self):
        # Route to the Master Log Folder
        self.log_path = LOG_PATHS.get("monit_or", "Monit.or_Routing_Log.txt")
        self._active_calls: Dict[str, float] = {}

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _mode_tag(self, mode: str) -> str:
        return "[LIVE]" if str(mode).lower() == "live" else "[MOCK]"

    def _strip_payload(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: self._strip_payload(v)
                for k, v in value.items()
                if k.lower() not in _STRIP_KEYS
            }
        if isinstance(value, (list, tuple)):
            return [self._strip_payload(v) for v in value]
        if isinstance(value, str):
            if len(value) > _TRUNCATE_LEN and _TRUNCATE_LEN == 0:
                return "[PAYLOAD STRIPPED]"
            return value[:_TRUNCATE_LEN] if _TRUNCATE_LEN else "[PAYLOAD STRIPPED]"
        return value

    def _write(self, line: str) -> None:
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            print(f"⚠️ [MONIT.OR FAULT] Could not write telemetry: {exc}")

    def log_api_call_initiated(
        self,
        provider: str,
        mode: str = "live",
        gate: str = "",
        role: str = "",
        call_id: Optional[str] = None,
    ) -> str:
        tag = self._mode_tag(mode)
        cid = call_id or f"{provider}_{time.time_ns()}"
        self._active_calls[cid] = time.perf_counter()
        parts = [f"[{self._timestamp()}] {tag} API Call Initiated: {provider}"]
        if gate:
            parts.append(f"Gate: {gate}")
        if role:
            parts.append(f"Role: {role}")
        parts.append(f"CallID: {cid}")
        self._write(" | ".join(parts))
        return cid

    def log_api_call_complete(
        self,
        provider: str,
        status: str,
        latency_s: Optional[float] = None,
        mode: str = "live",
        call_id: Optional[str] = None,
    ) -> None:
        tag = self._mode_tag(mode)
        if latency_s is None and call_id and call_id in self._active_calls:
            latency_s = round(time.perf_counter() - self._active_calls.pop(call_id), 3)
        latency_str = f"{latency_s}s" if latency_s is not None else "n/a"
        self._write(
            f"[{self._timestamp()}] {tag} Provider: {provider} | Status: {status} | Latency: {latency_str}"
        )

    def log_handoff(self, source: str, destination: str, mode: str = "live", pass_num: Optional[int] = None) -> None:
        tag = self._mode_tag(mode)
        line = f"[{self._timestamp()}] {tag} Handoff: {source} -> {destination}"
        if pass_num is not None:
            line += f" | Pass: {pass_num}"
        self._write(line)

    def log_routing_event(self, event: str, details: Optional[Dict[str, Any]] = None, mode: str = "live") -> None:
        tag = self._mode_tag(mode)
        safe_details = self._strip_payload(details or {})
        meta = " | ".join(f"{k}={v}" for k, v in safe_details.items()) if safe_details else ""
        line = f"[{self._timestamp()}] {tag} Route: {event}"
        if meta:
            line += f" | {meta}"
        self._write(line)

    def log_bus_event(
        self,
        action: str,
        destination_tag: str = "",
        envelope_id: str = "",
        pulse_result: str = "",
        mode: str = "live",
    ) -> None:
        tag = self._mode_tag(mode)
        parts = [f"[{self._timestamp()}] {tag} Bus: {action}"]
        if destination_tag:
            parts.append(f"Tag: {destination_tag}")
        if envelope_id:
            parts.append(f"Envelope: {envelope_id}")
        if pulse_result:
            parts.append(f"Pulse: {pulse_result}")
        self._write(" | ".join(parts))

    def log_api_call(self, model: str, status: str, latency: float) -> None:
        """Actively records the latency and status of WCR API handoffs."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [LIVE WIRETAP] Model: {model.upper():<10} | Status: {status:<15} | Latency: {latency:.2f}s\n"
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[MONIT.OR FAULT] Failed to write telemetry: {e}")


_monitor_instance: Optional[MonitorTelemetry] = None


def get_monitor() -> MonitorTelemetry:
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = MonitorTelemetry()
    return _monitor_instance