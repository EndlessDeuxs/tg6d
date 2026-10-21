#Regulator_Subsystem
# FILENAME: Twingate_regulator_votr.py
"""
Regulat.or Votr – Decentralized 4-Phase Voting Cascade
Explorer → Condensor → Conflict Check → Anchor Verdict
"""
from typing import Any, Dict, List, Optional

from ..InternalRegulations.Twingate_internal_config import get_severity_tag

SUMMON_ARBIT_R_FLAG = "SUMMON_ARBIT_R"
MANDATED_CONFLICT_INPUTS = ["C_R_ITIC", "DRIFT_R"]


class VotrSystem:
    def __init__(self):
        self.quaternion_motion_active: bool = False
        self.quaternion_payload: Optional[Dict[str, Any]] = None
        self.conflict_flag: bool = False
        self.next_wcr_mandated_inputs: List[str] = []
        self.escalation_payload: Optional[Dict[str, Any]] = None
        self.last_verdict: Optional[str] = None

    def quaternion_action_motion(self, proposal: dict) -> Dict[str, Any]:
        self.quaternion_motion_active = True
        self.quaternion_payload = {
            "proposal": proposal,
            "motion": "QUATERNION_ACTION_MOTION",
            "status": "TRIGGERED",
        }
        return self.quaternion_payload

    def explorer_vote(self, proposal: dict) -> bool:
        if proposal.get("dramatic_scene_shift", False):
            self.quaternion_action_motion(proposal)

        if "explorer_yay" in proposal:
            return bool(proposal["explorer_yay"])

        if proposal.get("explorer_nay", False) or proposal.get("risk_block", False):
            return False

        vote = proposal.get("vote")
        if vote is not None:
            return str(vote).lower() in ("yay", "yes", "true", "proceed", "1")

        return True

    def condensor_vote(self, proposal: dict, explorer_yay: bool) -> bool:
        if proposal.get("overreach", False) or proposal.get("condensor_veto", False):
            return False

        if "condensor_yay" in proposal:
            return bool(proposal["condensor_yay"])

        if not explorer_yay:
            return False

        return True

    def check_conflict(self, explorer_yay: bool, condensor_yay: bool) -> bool:
        self.conflict_flag = explorer_yay and not condensor_yay
        if self.conflict_flag:
            self.next_wcr_mandated_inputs = list(MANDATED_CONFLICT_INPUTS)
        else:
            self.next_wcr_mandated_inputs = []
        return self.conflict_flag

    def anchor_verdict(self, conflict_context: str) -> str:
        context_lower = conflict_context.lower()
        explorer_prevails = any(
            signal in context_lower
            for signal in ("proceed", "explorer outvotes", "explorer_prevails", "outvote condensor")
        )

        if explorer_prevails:
            self.last_verdict = "PROCEED"
            self.escalation_payload = None
            return self.last_verdict

        self.last_verdict = "ESCALATE"
        self.escalation_payload = {
            "verdict": "ESCALATE",
            "severity_level": 6,
            "severity_tag": get_severity_tag(6),
            "arbit_r_summon": True,
            "summon_flag": SUMMON_ARBIT_R_FLAG,
            "conflict_context": conflict_context,
            "mandated_wcr_inputs": list(self.next_wcr_mandated_inputs),
        }
        return self.last_verdict

    def receive_autocraft_override(self) -> None:
        """Triggered directly by the Autocraft Parser to initiate an emergency WCR vote."""
        self.override_active = True
        # Force the system into a mandated conflict check
        print(f"[VOT.R] EMERGENCY OVERRIDE TRIGGERED VIA AUTOCRAFT PARSER. Forcing conflict check Phase.")