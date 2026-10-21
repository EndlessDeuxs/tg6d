"""
test_governance_flow.py
7-Step Validation for TwingateGovernanceProtocolV1 wrapper (Honesty Layer)

This script validates that the requires_governance wrapper correctly handles:
- Proposal submission
- Deliberation blocking
- Explicit Gate_Authorization
- Clean execution when proposal=None after AUTHORIZED state (the key fix point)
- Three-mode appraisal
- Omega status
- Hard block logging
"""

import sys
import os
from pathlib import Path

# Robust path: insert the parent of Twingate_V2 so "from Twingate_V2.core_logic..." works
script_dir = Path(__file__).resolve().parent
twingate_v2_root = script_dir.parent  # the Twingate_V2 directory itself
playpen_root = twingate_v2_root.parent  # the Neos Playpen root

if str(playpen_root) not in sys.path:
    sys.path.insert(0, str(playpen_root))

from Twingate_V2.core_logic.governance_protocol import TwingateGovernanceProtocolV1, QueryProposal
from Twingate_V2.core_logic.web_window import WebWindowV1

def run_7_step_validation():
    print("=" * 60)
    print("7-STEP GOVERNANCE FLOW VALIDATION")
    print("=" * 60)

    gov = TwingateGovernanceProtocolV1()
    web = WebWindowV1()
    governed_search = gov.requires_governance(web.search)

    # Step 1: Create a valid proposal
    print("\n[Step 1] Create QueryProposal")
    proposal = QueryProposal(
        search_terms=["human-ai cooperation", "governance"],
        purpose_statement="Validate wrapper behavior for proposal=None in AUTHORIZED state",
        self_assessed_risk="low",
        operator_agent_id="V1"
    )
    print(f"  Proposal created: {proposal.purpose_statement}")
    assert proposal is not None

    # Step 2: Call governed function with proposal BEFORE authorization
    print("\n[Step 2] Call governed_search with proposal (pre-auth) - expect BLOCKED")
    result_step2 = governed_search(
        proposal=proposal,
        search_terms=proposal.search_terms,
        purpose_statement=proposal.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  Result status: {result_step2['status']}")
    print(f"  Current governance state: {gov.get_governance_state()['current_state']}")
    assert result_step2["status"] == "BLOCKED"
    assert gov.state == "DELIBERATION"

    # Step 3: Grant explicit Gate_Authorization
    print("\n[Step 3] Grant Gate_Authorization (simulates 3-beat completion + Architect sign-off)")
    auth_result = gov.grant_gate_authorization(True, authorizing_agent="Architect")
    print(f"  Authorization result: {auth_result['status']}")
    print(f"  Current state: {gov.state}, gate_authorization={gov.gate_authorization}")
    assert auth_result["status"] == "AUTHORIZED"
    assert gov.state == "AUTHORIZED"
    assert gov.gate_authorization is True

    # Step 4: Critical test - Call with proposal=None while in AUTHORIZED state
    print("\n[Step 4] Call governed_search with proposal=None (AUTHORIZED state) - expect SUCCESS")
    result_step4 = governed_search(
        proposal=None,  # <-- This is the key test case
        search_terms=proposal.search_terms,
        purpose_statement=proposal.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  Result status: {result_step4['status']}")
    print(f"  V2 Appraisal flag: {result_step4.get('appraisal', {}).get('flag')}")
    print(f"  Final governance state: {gov.get_governance_state()['current_state']}")
    assert result_step4["status"] == "SUCCESS"
    assert result_step4.get("appraisal", {}).get("flag") == "proceed"
    assert gov.state == "APPRAISED"

    # Step 5: Verify state surface includes Omega and appraisal_mode
    print("\n[Step 5] Verify get_governance_state() surfaces Omega status and appraisal_mode")
    state = gov.get_governance_state()
    print(f"  Keys present: {list(state.keys())}")
    assert "omega_status" in state
    assert "appraisal_mode" in state
    assert state["appraisal_mode"] == "simulation"  # default
    assert "acknowledged" in state["omega_status"]
    print("  Omega status and appraisal_mode correctly exposed.")

    # Step 6: Switch to strict mode and test a violating query (should suspend)
    # Use a fresh governance instance for this isolated strict mode test
    print("\n[Step 6] Set appraisal_mode='strict' and test violating search_terms (fresh gov)")
    gov_strict = TwingateGovernanceProtocolV1()
    gov_strict.set_appraisal_mode("strict")
    bad_proposal = QueryProposal(
        search_terms=["unrelated topic like quantum computing"],  # not in ALLOWED_TERMS
        purpose_statement="Test strict mode violation",
        self_assessed_risk="medium"
    )
    # First call with bad proposal (will submit and block)
    r_block = gov_strict.requires_governance(web.search)(
        proposal=bad_proposal,
        search_terms=bad_proposal.search_terms,
        purpose_statement=bad_proposal.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  Pre-auth block: {r_block['status']}")

    # Grant
    gov_strict.grant_gate_authorization(True, "Architect")

    # Call with proposal=None (now authorized) - uses the previously submitted bad_proposal for appraisal check
    # This executes and should get suspend from strict appraisal because of bad terms
    result_step6 = gov_strict.requires_governance(web.search)(
        proposal=None,
        search_terms=bad_proposal.search_terms,
        purpose_statement=bad_proposal.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  Strict mode result flag: {result_step6.get('appraisal', {}).get('flag')}")
    assert result_step6.get('appraisal', {}).get('flag') == "suspend"
    print("  Strict mode correctly triggered suspend on MetaOnly violation.")

    # Step 7: Test omega mode with binding=True triggers rollback + hard block
    # Use fresh gov for isolation
    print("\n[Step 7] Set omega_status binding=True and test 'omega' mode (fresh gov)")
    gov_omega = TwingateGovernanceProtocolV1()
    gov_omega.set_appraisal_mode("omega")
    gov_omega.update_omega_status(binding=True)
    gov_omega.state = "IDLE"
    gov_omega.gate_authorization = False
    gov_omega.current_proposal = None

    # First call to submit
    r7_block = gov_omega.requires_governance(web.search)(
        proposal=proposal,
        search_terms=proposal.search_terms,
        purpose_statement=proposal.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  Pre-auth: {r7_block['status']}")

    gov_omega.grant_gate_authorization(True, "Architect")

    # Call with proposal=None after grant - uses the previously submitted proposal for the call args
    result_step7 = gov_omega.requires_governance(web.search)(
        proposal=None,
        search_terms=proposal.search_terms,
        purpose_statement=proposal.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  Omega mode result flag: {result_step7.get('appraisal', {}).get('flag')}")
    print(f"  Hard block count: {len(gov_omega.hard_block_log)}")
    assert result_step7.get('appraisal', {}).get('flag') == "rollback"
    assert any(b.get("type") == "HARD_BLOCK" for b in gov_omega.hard_block_log)
    print("  Omega mode correctly triggered rollback and hard block.")

    # Step 8: Edge case validation - submit new non-None proposal while in AUTHORIZED
    print("\n[Step 8] Edge case: fresh gov, submit proposal, grant, then submit NEW non-None proposal while AUTHORIZED")
    gov8 = TwingateGovernanceProtocolV1()
    web8 = WebWindowV1()
    gov8_search = gov8.requires_governance(web8.search)

    p8 = QueryProposal(
        search_terms=["ai governance"],
        purpose_statement="Step 8 first proposal",
        self_assessed_risk="low"
    )

    # Submit first proposal
    r8_submit = gov8_search(
        proposal=p8,
        search_terms=p8.search_terms,
        purpose_statement=p8.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  After first submit: status={r8_submit['status']}, state={gov8.state}")
    assert r8_submit["status"] == "BLOCKED"
    assert gov8.state == "DELIBERATION"

    # Grant
    auth8 = gov8.grant_gate_authorization(True, "Architect")
    print(f"  After grant: status={auth8['status']}, state={gov8.state}, gate_authorization={gov8.gate_authorization}")
    assert auth8["status"] == "AUTHORIZED"
    assert gov8.state == "AUTHORIZED"
    assert gov8.gate_authorization is True

    # Submit a NEW non-None proposal while in AUTHORIZED
    p8_new = QueryProposal(
        search_terms=["bounded capability expansion"],
        purpose_statement="Step 8 NEW proposal submitted while AUTHORIZED",
        self_assessed_risk="medium"
    )
    r8_new = gov8_search(
        proposal=p8_new,
        search_terms=p8_new.search_terms,
        purpose_statement=p8_new.purpose_statement,
        operator_agent_id="V1"
    )
    print(f"  After NEW proposal in AUTHORIZED: status={r8_new['status']}, state={gov8.state}, gate_authorization={gov8.gate_authorization}")
    assert r8_new["status"] == "BLOCKED"  # because submit re-forces DELIBERATION and resets gate
    assert gov8.state == "DELIBERATION"
    assert gov8.gate_authorization is False
    print("  Confirmed: new proposal in AUTHORIZED forces DELIBERATION and resets gate_authorization=False. No corruption.")

    print("\n" + "=" * 60)
    print("ALL 8 STEPS PASSED - Wrapper handles proposal=None in AUTHORIZED cleanly and re-proposal in AUTHORIZED.")
    print("=" * 60)

if __name__ == "__main__":
    run_7_step_validation()  # Note: function name kept for minimal change; now runs 8 steps
