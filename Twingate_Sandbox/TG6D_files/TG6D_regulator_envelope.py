#Regulator_Subsystem
# FILENAME: Twingate_regulator_envelope.py
"""
Regulat.or Envelope – The Standard Data Packet
The required wrapper for all messages passing across the Regulat.or bus.
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict
from .Twingate_regulator_config import ClearanceTier, SystemTags

@dataclass
class RegulatorEnvelope:
    origin: str
    destination_tag: SystemTags
    clearance_level: ClearanceTier
    payload: Any
    priority_id: int = 0
    envelope_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)