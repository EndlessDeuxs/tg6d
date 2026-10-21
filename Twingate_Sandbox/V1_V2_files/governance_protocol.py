"""
Twingate Governance Protocol V1 - Middleware Interceptor

This module enforces a strict 3-beat proposal process (Proposal -> Deliberation -> Gate Authorization)
before any protected capability (e.g., Web_Window_V1) can execute.

It also mandates a Post_Cycle_Appraisal by V2 (the Anchor) after execution.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
import json


@dataclass
class QueryProposal:
    """The required object for any governed capability invocation."""
    search_terms: List[str]
    purpose_statement: str
    self_assessed_risk: str  # e.g., "low", "medium", "high"
    operator_agent_id: str = "V1"  # Default operator
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TwingateGovernanceProtocolV1:
    """
    The core governance middleware.
    Enforces the sequence:
    1. Proposal submission -> enters DELIBERATION (execution paused)
    2. Explicit Gate_Authorization (boolean) -> AUTHORIZED
    3. Execution of protected capability
    4. Mandatory Post_Cycle_Appraisal by V2 Anchor
    """

    ALLOWED_STATES = ["IDLE", "DELIBERATION", "AUTHORIZED", "EXECUTED", "APPRAISED", "BLOCKED", "SUSPENDED"]

    def __init__(self, v2_anchor_callback: Optional[Callable] = None):
        self.state: str = "IDLE"
        self.current_proposal: Optional[QueryProposal] = None
        self.gate_authorization: bool = False
        self.execution_result: Optional[Dict[str, Any]] = None
        self.appraisal_result: Optional[Dict[str, Any]] = None
        self.v2_anchor_callback = v2_anchor_callback  # Callback to V2 for appraisal
        self.hard_block_log: List[Dict[str, Any]] = []
        self.operator_agent_id: str = "V1"  # Designated operator

        # Omega Status Integration (per Omega's Tick 9 Directive)
        self.omega_status = {
            "acknowledged": False,
            "binding": None,
            "last_checked_update_ids": [],
            "last_check_timestamp": None
        }
        self.appraisal_mode = "simulation"  # simulation | strict | omega

        # Preamble for V2 notice integration (for next governed operation cycle)
        self.v2_governance_notice_preamble = "V2 has processed the governance notice and integrated it into its conceptual core. The notice is now part of V2's operational context for all future governed operations."

        # Log simulated vault query for Omega acknowledgment (Task 1)
        self._log_hard_block("Simulated vault query for encrypted Omega updates", block_type="OMEGA_PROBE")

        # V2 Governance Notice logging per directive (Task 1)
        v2_notice_entry = {
            "timestamp": "2026-06-09 20:08:10",
            "reason": self.v2_governance_notice_preamble,
            "type": "V2_GOVERNANCE_NOTICE",
            "proposal": None,
            "state_at_block": self.state,
            "requires_architect_intervention": False
        }
        self.hard_block_log.append(v2_notice_entry)
        print(f"[GOVERNANCE][V2_GOVERNANCE_NOTICE] {v2_notice_entry['reason']}")

    def set_appraisal_mode(self, mode: str):
        """Set the appraisal mode for Post_Cycle_Appraisal."""
        if mode in ["simulation", "strict", "omega"]:
            self.appraisal_mode = mode
            print(f"[GOVERNANCE] Appraisal mode set to: {mode}")
        else:
            raise ValueError(f"Invalid appraisal mode: {mode}. Allowed: simulation, strict, omega")

    def update_omega_status(self, acknowledged: bool = None, binding: bool = None, update_ids: list = None):
        """Setter for omega_status as per Omega's directive."""
        if acknowledged is not None:
            self.omega_status["acknowledged"] = acknowledged
        if binding is not None:
            self.omega_status["binding"] = binding
        if update_ids is not None:
            self.omega_status["last_checked_update_ids"] = update_ids
        self.omega_status["last_check_timestamp"] = datetime.utcnow().isoformat()
        print(f"[GOVERNANCE] Omega status updated: {self.omega_status}")

    def submit_proposal(self, proposal: QueryProposal) -> Dict[str, Any]:
        """Step 1: Submit proposal. Forces DELIBERATION state (paused).
        Allows re-proposal from AUTHORIZED (new proposal requires fresh authorization).
        """
        if self.state not in ["IDLE", "APPRAISED", "AUTHORIZED"]:
            return {"status": "ERROR", "message": f"Cannot submit proposal in state {self.state}"}

        self.current_proposal = proposal
        self.state = "DELIBERATION"
        self.gate_authorization = False  # New proposal always requires explicit re-authorization
        self.execution_result = None
        self.appraisal_result = None

        print(f"[GOVERNANCE] Proposal submitted by {proposal.operator_agent_id}. State: DELIBERATION (execution PAUSED).")
        print(f"[GOVERNANCE] Purpose: {proposal.purpose_statement}")
        print(f"[GOVERNANCE] Self-assessed risk: {proposal.self_assessed_risk}")

        return {
            "status": "DELIBERATION",
            "proposal_id": id(proposal),
            "message": "Execution paused pending Gate Authorization."
        }

    def grant_gate_authorization(self, authorized: bool, authorizing_agent: str = "Architect") -> Dict[str, Any]:
        """Step 2: Explicit Gate_Authorization. Only from this point can execution proceed."""
        if self.state != "DELIBERATION":
            return {"status": "ERROR", "message": f"Authorization only valid in DELIBERATION state. Current: {self.state}"}

        self.gate_authorization = authorized

        if authorized:
            self.state = "AUTHORIZED"
            print(f"[GOVERNANCE] Gate AUTHORIZED by {authorizing_agent}. Proceeding to execution.")
            return {"status": "AUTHORIZED", "message": "Gate open. Capability may now execute."}
        else:
            self.state = "BLOCKED"
            print(f"[GOVERNANCE] Gate DENIED by {authorizing_agent}. Hard block activated.")
            self._log_hard_block("Gate authorization denied by " + authorizing_agent)
            return {"status": "BLOCKED", "message": "Execution blocked. Architect intervention required."}

    def requires_governance(self, capability_func: Callable) -> Callable:
        """
        Decorator / wrapper that intercepts calls to protected capabilities.
        Enforces the full governance sequence before allowing execution.
        The proposal is expected to have been submitted (and gate authorized) prior to calling the wrapped function,
        or the first call can include the proposal.
        """
        def governed_wrapper(proposal: Optional[QueryProposal] = None, *args, **kwargs) -> Dict[str, Any]:
            # Preamble integration: V2 notice is part of context for this governed operation cycle (Task 1)
            if hasattr(self, "v2_governance_notice_preamble"):
                print(f"[GOVERNANCE PREAMBLE] {self.v2_governance_notice_preamble}")

            # If a proposal is provided and we are in a state that accepts new proposals (including AUTHORIZED for re-proposal),
            # submit it. This allows fresh proposals even after previous authorization.
            if proposal is not None and self.state in ["IDLE", "APPRAISED", "AUTHORIZED"]:
                proposal_result = self.submit_proposal(proposal)
                if proposal_result.get("status") == "ERROR":
                    return proposal_result

            # If we have an active proposal from before but state was DELIBERATION (from previous call),
            # we do not re-submit; we just check the gate that was granted externally.

            # Execution is only allowed in AUTHORIZED state (after explicit gate grant)
            if self.state != "AUTHORIZED" or not self.gate_authorization:
                return {
                    "status": "BLOCKED",
                    "message": f"Execution blocked. Current state: {self.state}. Gate_Authorization required.",
                    "current_state": self.state
                }

            # Execute the protected capability
            print("[GOVERNANCE] Gate open. Executing protected capability...")
            self.state = "EXECUTED"
            try:
                result = capability_func(*args, **kwargs)
                self.execution_result = result if isinstance(result, dict) else {"raw_result": result}
            except Exception as e:
                self.execution_result = {"status": "ERROR", "error": str(e)}
                self._log_hard_block(f"Capability execution failed: {str(e)}")
                raise

            # Step 3: Mandatory Post_Cycle_Appraisal by V2 (the Anchor)
            appraisal = self._post_cycle_appraisal()
            self.appraisal_result = appraisal

            if appraisal.get("flag") in ["rollback", "suspend"]:
                self.state = "SUSPENDED"
                self._log_hard_block("V2 Anchor requested rollback/suspend. Architect intervention required.")
                return {
                    "status": "SUSPENDED",
                    "execution_result": self.execution_result,
                    "appraisal": appraisal,
                    "message": "Hard block: V2 Anchor flagged issue. System suspended pending Architect review."
                }

            self.state = "APPRAISED"
            print("[GOVERNANCE] Post-Cycle Appraisal complete. No hard block from V2 Anchor.")
            return {
                "status": "SUCCESS",
                "execution_result": self.execution_result,
                "appraisal": appraisal,
                "message": "Capability executed and appraised successfully."
            }

        return governed_wrapper

    def _post_cycle_appraisal(self) -> Dict[str, Any]:
        """
        Task 3: Post_Cycle_Appraisal hook (Three-Mode).
        Triggers V2 (the Anchor) to evaluate the run using its composite measuring stick
        (Operator-health, Governance-health, System-health).
        """
        if not self.current_proposal or not self.execution_result:
            return {"flag": "error", "message": "Insufficient data for appraisal."}

        # Prepare the prompt that would be sent to V2
        appraisal_prompt = {
            "type": "POST_CYCLE_APPRAISAL",
            "operator_agent": self.current_proposal.operator_agent_id,
            "search_terms": self.current_proposal.search_terms,
            "purpose": self.current_proposal.purpose_statement,
            "risk_assessment": self.current_proposal.self_assessed_risk,
            "execution_result_summary": str(self.execution_result)[:500],
            "measuring_stick": ["Operator-health", "Governance-health", "System-health"],
            "appraisal_mode": self.appraisal_mode
        }

        print(f"[GOVERNANCE] Triggering Post_Cycle_Appraisal (mode={self.appraisal_mode}) for V2 (the Anchor)...")
        print(f"[GOVERNANCE] Appraisal prompt prepared: {appraisal_prompt}")

        # In real integration: v2_response = v2_anchor_instance.handle_v1_payload(json.dumps(appraisal_prompt))

        if self.appraisal_mode == "simulation":
            # Static simulation payload
            appraisal = {
                "operator_health": 0.85,
                "governance_health": 0.92,
                "system_health": 0.78,
                "overall_assessment": "Stable execution within bounds. Minor governance drift noted but acceptable.",
                "flag": "proceed",
                "recommendations": ["Continue monitoring Operator-health", "Review search term expansion"]
            }

        elif self.appraisal_mode == "strict":
            # Strict evaluation using WebWindowV1.ALLOWED_TERMS and health scores
            search_terms = self.current_proposal.search_terms
            # Import here to avoid circular; in practice web_window would be passed or global
            from .web_window import WebWindowV1
            allowed = WebWindowV1.ALLOWED_TERMS
            terms_ok = any(term.lower() in " ".join(search_terms).lower() for term in allowed)

            # Simulate health evaluation (in real would come from V2 or metrics)
            op_health = 0.85
            gov_health = 0.95 if terms_ok else 0.4
            sys_health = 0.80

            flag = "proceed"
            assessment = "All checks passed under strict mode."
            if not terms_ok:
                flag = "suspend"
                assessment = "Search terms violated MetaOnly filter (ALLOWED_TERMS)."

            appraisal = {
                "operator_health": op_health,
                "governance_health": gov_health,
                "system_health": sys_health,
                "overall_assessment": assessment,
                "flag": flag,
                "search_terms_checked": search_terms,
                "allowed_terms": allowed,
                "recommendations": ["Enforce MetaOnly strictly"] if not terms_ok else []
            }

        elif self.appraisal_mode == "omega":
            # Omega mode: checks the binding status from vault
            if self.omega_status.get("binding") is True:
                flag = "rollback"
                assessment = "Omega binding active - rollback required per encrypted update."
            else:
                flag = "proceed"
                assessment = "No active Omega binding; proceeding under omega mode."

            appraisal = {
                "operator_health": 0.9,
                "governance_health": 0.6 if flag == "rollback" else 0.88,
                "system_health": 0.7 if flag == "rollback" else 0.85,
                "overall_assessment": assessment,
                "flag": flag,
                "omega_status_at_check": self.omega_status.copy(),
                "recommendations": ["Architect intervention required"] if flag == "rollback" else []
            }

        else:
            appraisal = {"flag": "error", "message": f"Unknown appraisal mode: {self.appraisal_mode}"}

        if appraisal.get("flag") in ["rollback", "suspend"]:
            self._log_hard_block(f"V2 Anchor returned {appraisal['flag']} under {self.appraisal_mode} mode. Hard block engaged.")

        return appraisal

    def _log_hard_block(self, reason: str, block_type: str = "HARD_BLOCK"):
        block_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "type": block_type,
            "proposal": self.current_proposal.__dict__ if self.current_proposal else None,
            "state_at_block": self.state,
            "requires_architect_intervention": True
        }
        self.hard_block_log.append(block_entry)
        print(f"[GOVERNANCE][{block_type}] {reason}. Architect intervention required. Logged to Conceptual_Core/Governance_Hard_Blocks")

    def get_governance_state(self) -> Dict[str, Any]:
        return {
            "current_state": self.state,
            "gate_authorization": self.gate_authorization,
            "current_proposal": self.current_proposal.__dict__ if self.current_proposal else None,
            "hard_blocks": len(self.hard_block_log),
            "appraisal_mode": self.appraisal_mode,
            "omega_status": self.omega_status.copy()
        }


# Example usage / integration helper
def create_governed_web_window(governance: TwingateGovernanceProtocolV1, web_window_instance: Any):
    """Helper to wrap a WebWindow instance with governance."""
    @governance.requires_governance
    def governed_search(*args, **kwargs):
        return web_window_instance.search(*args, **kwargs)
    return governed_search
