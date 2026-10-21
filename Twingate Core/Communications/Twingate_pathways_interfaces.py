#Communications_Pathways
# FILENAME: Twingate_pathways_interfaces.py
"""
Communications Layer – Type Definitions
Clean interfaces for the relay loop.
"""
from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass, field

@dataclass
class GateOutput:
    gate_name: str
    role: str
    content: str
    model_used: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelayContext:
    user_prompt: str
    tone: str
    mood: str
    recursion_depth: int
    current_cycle: int
    previous_outputs: List[GateOutput] = field(default_factory=list)
    chain_context: str = ""
    rag_memories: List[str] = field(default_factory=list)
    next_directive: str = ""
    
    # HUD & Subsystem Variables
    chronos_stamp: str = ""
    ek_mood_tensor: str = ""
    confidence_score: float = 1.0
    chrono_tick: str = ""
    confidence: float = 1.0
    
    # Deuxl Core / Bean Counter State
    gate_flips_remaining: Dict[str, int] = field(default_factory=dict)
    arbit_r_calls_remaining: int = 1

@dataclass
class RouterRequest:
    gate_name: str
    role: str
    context: str
    max_tokens: int = 4096
    temperature: float = 0.7
    system_hud: str = ""
    arbit_r_capacity: int = 0
    pass_count_remaining: int = 3

@dataclass
class RouterResponse:
    success: bool
    content: str
    model_used: str
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    circuit_breaker: bool = False