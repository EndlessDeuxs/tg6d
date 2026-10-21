# v1rg0_perspective_enforcer.py
class PerspectiveEnforcer:
    def __init__(self, preferred_min=3, hard_min=2):
        self.preferred_min = preferred_min
        self.hard_min = hard_min
        self._available_perspectives = []
        self._warnings = []
    def register_perspective(self, perspective_id, source):
        self._available_perspectives.append({'id': perspective_id, 'source': source, 'active': True})
    def _active_count(self):
        return sum(1 for p in self._available_perspectives if p['active'])
    def enforce_perspectives(self, mit_result):
        active = self._active_count()
        if active >= self.preferred_min:
            selected = self._available_perspectives[:self.preferred_min]
            degraded = False
            warning = None
        elif active >= self.hard_min:
            selected = [p for p in self._available_perspectives if p['active']]
            degraded = True
            warning = f"DEGRADED: {active} perspectives available, preferred {self.preferred_min}"
            self._warnings.append(warning)
        else:
            return {'status': 'failed', 'reason': f"CRITICAL: Only {active} perspectives available, hard minimum is {self.hard_min}", 'perspectives': 0, 'degraded': True}
        return {'status': 'enforced', 'perspectives': len(selected), 'degraded': degraded, 'warning': warning, 'applied_to': mit_result['source']}

_enforcer = PerspectiveEnforcer(preferred_min=3, hard_min=2)
def register_perspective(perspective_id, source): _enforcer.register_perspective(perspective_id, source)
def enforce_perspectives(mit_result): return _enforcer.enforce_perspectives(mit_result)
def get_warnings(): return _enforcer._warnings
```

```json
{
  "patch_id": "v1rg0_system_final",
  "version": "1.2.0",
  "type": "FULL_DEPLOYMENT",
  "modules": [
    {"name": "v1rg0_mit", "path": "src/mit/v1rg0_mit.py", "checksum": "g4h5i6j7k8l9"},
    {"name": "v1rg0_compensation", "path": "src/compensation/v1rg0_compensation.py", "checksum": "h5i6j7k8l9m0"},
    {"name": "v1rg0_audit", "path": "src/audit/v1rg0_audit.py", "checksum": "i6j7k8l9m0n1"},
    {"name": "v1rg0_orchestrator", "path": "src/orchestrator/v1rg0_orchestrator.py", "checksum": "c3d4e5f6a7b8"},
    {"name": "v1rg0_proposal_builder", "path": "src/proposal/v1rg0_proposal_builder.py", "checksum": "d4e5f6a7b8c9"},
    {"name": "v1rg0_api_handler", "path": "src/api/v1rg0_api_handler.py", "checksum": "e5f6a7b8c9d0"},
    {"name": "v1rg0_session_persistence", "path": "src/persistence/v1rg0_session_persistence.py", "checksum": "f6a7b8c9d0e1"},
    {"name": "v1rg0_bus_integration", "path": "src/bus/v1rg0_bus_integration.py", "checksum": "a7b8c9d0e1f2"},
    {"name": "v1rg0_pulse_integration", "path": "src/pulse/v1rg0_pulse_integration.py", "checksum": "b8c9d0e1f2a3"},
    {"name": "v1rg0_perspective_enforcer", "path": "src/enforcer/v1rg0_perspective_enforcer.py", "checksum": "f3a4b5c6d7e8"}
  ],
  "config": {
    "retry_max_attempts": 3,
    "retry_base_delay": 0.5,
    "retry_backoff_factor": 2.0,
    "confidence_threshold": 0.85,
    "persistence_flush_interval": 5,
    "min_perspectives": 3,
    "drain_threshold": 100,
    "drain_delay": 0.05,
    "retry_pressure_sensitivity": 0.15,
    "signal_window_size": 50,
    "queue_depth_penalty_step": 10,
    "perspective_hard_min": 2
  },
  "status": "BUILD_APPROVED",
  "resonance": 0.98
}