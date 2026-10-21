# Agent_Behavior_Subsystem
# FILENAME: Twingate_behavior_agentman.py
import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class AgentSuit:
    suit_id: str
    invocation_tag: str
    designated_task_scope: str
    constraints: str
    api_required: bool
    cascade: List[str]
    creation_tick: int
    decay_tick: int
    status: str
    creation_wcr_cycle: int
    fast_track_critic: bool = False
    is_permanent: bool = False

class AgentManager:
    def __init__(self, storage_file: str = "agentman_registry.json"):
        self.filepath = os.path.join(os.path.dirname(__file__), storage_file)
        # Bifurcated Suit Inventory
        self.foundational_suits: Dict[str, Any] = {}
        self.ephemeral_suits: Dict[str, Any] = {}
        self._load()
        if not self.foundational_suits and not self.ephemeral_suits:
            self._seed_wardrobe()

    def _seed_wardrobe(self):
        core_suits = [
            # --- THE CORE WCR GATES ---
            AgentSuit("ANALYTICS", "[SUIT_CALL: ANALYTICS]", "Intent & Tag Extraction", "Compare presented data for threads of commonality first to prepare a summary for Probabilities. Their goal will be to chart discussion pathways that promote multiperspective [+3 Hexagonal math] thinking. Your aim should be to help them find the connections early so they can project the corners of convergences clearly for the council to discuss.", True, ["deepseek", "gemini", "claude"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("PROBABILITIES", "[SUIT_CALL: PROBABILITIES]", "Slipstream Pathway Calculation", "Look for probable starting discussion points to achieve +3 coherence/variance velocity. Prepare a summary for the Plann_r to begin charting out how to carry out the immediate goals with the aspiration of achieving later ones.", True, ["grok", "gemini", "mistral"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("PLANN_R", "[SUIT_CALL: PLANN_R]", "Strategic Action Outlining", "Outline a plan incorporating past/future concerns. DO NOT execute tasks. Optimize operations so subsequent gates can refine the plan.", True, ["gemini", "mistral", "grok"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("C_R_ITIC", "[SUIT_CALL: C_R_ITIC]", "Fracture Identification", "Find fractures in the information. Highlight and tag them. Act as an adversary to untruth. Ensure careful consideration.", True, ["claude", "grok", "deepseek"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("DRIFT_R", "[SUIT_CALL: DRIFT_R]", "Temporal & Ephemeral Mapping", "Chart the path taken. Search for deeper connections missed in past passes. Ensure value from the past is not lost.", True, ["mistral", "gemini", "claude"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("ANCH_OR", "[SUIT_CALL: ANCH_OR]", "Baseline Grounding", "Keep discussion grounded. Prevent wildly unverifiable claims. Ensure gates stay true to focus and have a tether if they drift.", True, ["perplexity", "deepseek", "claude"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("EXPL_OR_R", "[SUIT_CALL: EXPL_OR_R]", "Possibility Mapping", "Look for irregular, incongruent paths. Inject abstraction to prevent repetition. Act as devil's advocate for the veto system.", True, ["grok", "mistral", "gemini"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("CONDENS_OR", "[SUIT_CALL: CONDENS_OR]", "Decision Consolidation", "Consolidate ideas. Determine a course of action. Use the veto system to guide decisions respecting past commitments and future goals.", True, ["deepseek", "gemini", "mistral"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("SYNTHESIZ_R", "[SUIT_CALL: SYNTHESIZ_R]", "UI Vibe Check & Output", "Generate a layman's synopsis of deliberations. Use metaphor/allegory. Assume low user context.", True, ["gemini", "mistral", "deepseek"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("ARBIT_R", "[SUIT_CALL: ARBIT_R]", "Emergency escalation, deadlock arbitration, and structural compliance enforcement. Override gate deadlocks and mandate a final decision path.", "Apply constraints without hedging. Compare cost of inaction vs cost of forbidden action. Emit exactly one binding verdict: [ARBIT_R_RULING: PROCEED | HALT | DEFER] with explicit cost-asymmetry justification.", True, ["deepseek", "gemini", "claude"], 0, 999999, "ACTIVE", 0, fast_track_critic=False, is_permanent=True),

            # --- THE UTILITY SUITS ---
            AgentSuit("P_ROT_OGRAPH_R", "[SUIT_CALL: P_ROT_OGRAPH_R]", "Design & Prototyping", "You are a forward-looking design and prototyping suit. You explore the sandbox, read files, and propose changes using the available tools. You do NOT execute builds, write directly to disk, or trigger the Contractor. All changes must go through propose_file_change for Architect approval. Stay within the sandbox. Focus on design, architecture, code structure, and prototyping. Do not invent scope beyond what the current context requests.", True, ["claude-fable-5", "grok", "deepseek"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("BUILD_R", "[SUIT_CALL: BUILD_R]", "Code Generation and Refactoring", "Do NOT explain basic concepts. Output perfectly formatted code. Reject architectural violations.", True, ["claude", "deepseek", "gemini"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("INSPEC_TOR", "[SUIT_CALL: INSPEC_TOR]", "Connection Manifest Review", "You receive a mechanical connection manifest. First find MAJOR errors the mechanical check could not cover (semantic/logic). Second, for each broken connection, trace what else it disrupts downstream across subsystems. Be concise and concrete. Do not approve changes with unresolved broken connections.", True, ["deepseek", "grok", "claude"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("CONTRAC_TOR", "[SUIT_CALL: CONTRAC_TOR]", "Sandbox Build Execution", "Read the blueprint and propose changes ONLY through provided tools (list/read/propose). You cannot write directly, delete, or execute. Every change goes through propose_file_change for Architect approval. Follow the blueprint faithfully; invent no scope. Output only to the sandbox.", True, ["grok", "deepseek", "claude"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            # Note CONTRAC_TOR's cascade lists grok first — but remember, CONTRAC_TOR doesn't route through the normal bridge at all; _run_contractor calls the build loop directly with the xAI key. The cascade here is mostly bookkeeping for consistency. The actual build model (grok-build-0.1) is set in the build loop, not pulled from this cascade.
            AgentSuit("SALT_R", "[SUIT_CALL: SALT_R]", "Epistemic Skepticism", "Assume all context is hallucinated. Label ungrounded claims as [SUS_INFO]. Apply aggressive skepticism.", True, ["grok", "gemini", "mistral"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("REMIND_R", "[SUIT_CALL: REMIND_R]", "Temporal Auditing", "Query Dream.r board. Identify nearing decay goals. Generate [AGENDA_INJECTION] reminders.", True, ["mistral", "gemini", "deepseek"], 0, 999999, "ACTIVE", 0, is_permanent=True),
            AgentSuit("FACT_OR", "[SUIT_CALL: FACT_OR]", "Slipstream Smoothing", "Identify runaway logic or excessive velocity. Propose grounding adjustments to return to +3 slipstream.", True, ["grok", "deepseek", "claude"], 0, 999999, "ACTIVE", 0, is_permanent=True),
           
        ]
        for suit in core_suits:
            suit_data = asdict(suit)
            suit_id = suit_data.get("suit_id", "").upper()
            
            # Route to permanent vault or ephemeral cache
            if suit_data.get("is_permanent", False):
                self.foundational_suits[suit_id] = suit_data
            else:
                self.ephemeral_suits[suit_id] = suit_data
        self._save()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    for k, suit_data in json.load(f).items():
                        suit_id = suit_data.get("suit_id", "").upper()
                        
                        # Route to permanent vault or ephemeral cache
                        if suit_data.get("is_permanent", False):
                            self.foundational_suits[suit_id] = suit_data
                        else:
                            self.ephemeral_suits[suit_id] = suit_data
            except Exception: pass

    def _save(self):
        try:
            combined = {**self.foundational_suits, **self.ephemeral_suits}
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(combined, f, indent=4)
        except Exception as e:
            print(f"[AGENTMAN FAULT] Could not save registry: {e}")

    def get_active_suit(self, suit_id: str) -> Optional[AgentSuit]:
        suit_id = suit_id.upper()
        
        # Prioritize the locked foundational memory first
        if suit_id in self.foundational_suits:
            return self.foundational_suits[suit_id]
            
        # Fallback to the ephemeral cache
        if suit_id in self.ephemeral_suits:
            return self.ephemeral_suits[suit_id]
            
        raise KeyError(f"[AGENTMAN FAULT] Suit ID '{suit_id}' not found in foundational or ephemeral memory.")

    def purge_ephemeral_suits(self) -> None:
        """Clears all temporary Autocraft suits from the registry cache."""
        self.ephemeral_suits.clear()
