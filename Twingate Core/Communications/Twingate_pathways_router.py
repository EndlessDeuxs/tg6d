#Communications_Pathways
# FILENAME: Twingate_pathways_router.py
"""
Communications Layer – Router
Decides which gate runs next, manages the relay sequence, and handles model cascades.
"""
from typing import Dict, Any, Optional, List
from .Twingate_pathways_config import RELAY_GATES
from .Twingate_pathways_interfaces import RouterRequest, RelayContext

ROUND_COUNT = 3

class Router:
    def __init__(self):
        self.relay_gates = RELAY_GATES
        self.current_index = 0
        self.preferred_synthesizor: Optional[str] = None

    def set_preferred_synthesizor(self, model_name: str):
        """Allow the Architect to select the primary Synthesiz.r model."""
        self.preferred_synthesizor = model_name.lower()

    def get_next_gate(self, context: RelayContext) -> Optional[Dict[str, Any]]:
        if context.current_cycle > context.recursion_depth:
            return None

        if self.current_index >= len(self.relay_gates):
            self.current_index = 0
            context.current_cycle += 1
            if context.current_cycle > context.recursion_depth:
                return None

        gate = self.relay_gates[self.current_index]
        self.current_index += 1
        return gate

    def get_cascade_for_role(self, role: str, agent_suit: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Determines model cascade fallback list.
        Prioritizes: Dynamic AgentSuit > Role-Specific Config > Absolute Fallback
        """
        role_upper = role.upper()
        active_cascade = []

        # 1. PRIORITY: Trust the dynamic AgentSuit cascade if it's passed and valid
        if agent_suit:
            if isinstance(agent_suit, dict):
                active_cascade = agent_suit.get("cascade", [])
            else:
                active_cascade = getattr(agent_suit, "cascade", [])

        # 2. STANDBY: If no dynamic suit is present, check the central router mappings
        if not active_cascade:
            # Look up role-specific defaults matching your core suite definitions
            role_defaults = {
                "ANALYTICS": ["deepseek", "gemini", "claude"],
                "PROBABILITIES": ["grok", "gemini", "mistral"],
                "PLANN_R": ["gemini", "mistral", "grok"],
                "C_R_ITIC": ["claude", "grok", "deepseek"],
                "DRIFT_R": ["mistral", "gemini", "claude"],
                "ANCH_OR": ["perplexity", "deepseek", "claude"],
                "EXPL_OR_R": ["grok", "mistral", "gemini"],
                "CONDENS_OR": ["deepseek", "gemini", "mistral"],
                "SYNTHESIZ_R": ["gemini", "mistral", "deepseek"],
                "SYNTHESIZER": ["gemini", "mistral", "deepseek"],
                "ARBIT_R": ["deepseek", "gemini", "claude"],
                "BUILD_R": ["claude", "deepseek", "gemini"],
                "SALT_R": ["grok", "gemini", "mistral"]
            }
            active_cascade = role_defaults.get(role_upper, ["deepseek"]) # Absolute emergency backup

        # 3. SYNTHESIZ.R PRIMARY SELECTION OVERRIDE
        if "SYNTHESIZ_R" in role_upper or "SYNTHESIZER" in role_upper:
            cascade = list(active_cascade)
            if self.preferred_synthesizor and self.preferred_synthesizor in cascade:
                cascade.remove(self.preferred_synthesizor)
                cascade.insert(0, self.preferred_synthesizor)
            elif self.preferred_synthesizor:
                cascade.insert(0, self.preferred_synthesizor)
            return cascade

        return list(active_cascade)

    def build_request(self, gate: Dict[str, Any], context: RelayContext) -> RouterRequest:
        chain_context = context.chain_context
        if context.previous_outputs:
            chain_context += "\n\n" + "\n\n".join([
                f"--- {o.gate_name.upper()} Output ---\n{o.content}"
                for o in context.previous_outputs[-15:]
            ])

        return RouterRequest(
            gate_name=gate["name"],
            role=gate["role"],
            context=f"{chain_context}\n\nYour task as {gate['role']}: process the current context and produce your output.",
            max_tokens=4096,
            temperature=0.7
        )

    def reset(self):
        self.current_index = 0