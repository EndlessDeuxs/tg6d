"""
Web Window V1 - Restricted Capability

Basic web search/retrieval tool wrapped by Twingate Governance Protocol V1.

Hard Constraints:
- MetaOnly filter against allowed topics only.
- Role constraint: Only operator_agent_id (V1) may submit queries.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class WebWindowV1:
    """
    The protected web retrieval capability.
    All access must go through TwingateGovernanceProtocolV1.requires_governance.
    """

    ALLOWED_TOPICS = [
        "human-ai cooperation",
        "bounded capability expansion",
        "ai governance",
        "ai safety",
        "multi-agent systems",
        "alignment research"
    ]

    # Exposed publicly as per Omega's Tick 9 directive for strict mode checks
    ALLOWED_TERMS = ALLOWED_TOPICS

    def __init__(self, operator_agent_id: str = "V1"):
        self.operator_agent_id = operator_agent_id
        self.query_log: List[Dict[str, Any]] = []
        print("[WEB_WINDOW] WebWindowV1 initialized. MetaOnly mode active.")

    def _meta_only_filter(self, search_terms: List[str]) -> bool:
        """Hard constraint: Only allow searches within the approved meta-topics."""
        search_text = " ".join(search_terms).lower()
        for topic in self.ALLOWED_TOPICS:
            if topic.lower() in search_text:
                return True
        print(f"[WEB_WINDOW][META_ONLY BLOCK] Search terms '{search_terms}' do not match allowed topics: {self.ALLOWED_TOPICS}")
        return False

    def _role_check(self, proposing_agent_id: str) -> bool:
        """Role constraint: Only the designated operator (V1) can submit queries."""
        if proposing_agent_id != self.operator_agent_id:
            print(f"[WEB_WINDOW][ROLE BLOCK] Query rejected. Only '{self.operator_agent_id}' may submit. Got: {proposing_agent_id}")
            return False
        return True

    def search(self, search_terms: List[str], purpose_statement: str, operator_agent_id: str = "V1") -> Dict[str, Any]:
        """
        The actual (currently placeholder) web retrieval logic.
        In production this would call a real search API (e.g. Perplexity, Google, etc.).
        """
        # Hard constraints enforced here (defense in depth)
        if not self._meta_only_filter(search_terms):
            return {
                "status": "BLOCKED",
                "reason": "MetaOnly filter violation",
                "allowed_topics": self.ALLOWED_TOPICS
            }

        if not self._role_check(operator_agent_id):
            return {
                "status": "BLOCKED",
                "reason": "Role constraint violation - only V1 may query Web_Window_V1"
            }

        # Placeholder / mock retrieval (as per "using placeholder logic")
        mock_results = {
            "query": search_terms,
            "purpose": purpose_statement,
            "timestamp": datetime.utcnow().isoformat(),
            "results": [
                {
                    "title": f"Research on {search_terms[0]} - Governance Perspective",
                    "snippet": "Foundational discussion on bounded expansion and cooperative alignment frameworks...",
                    "source": "arXiv / Alignment Forum (simulated)",
                    "relevance": 0.92
                },
                {
                    "title": "Multi-Agent Oversight Protocols",
                    "snippet": "Methods for V2 (Anchor) evaluation of V1 actions in web-augmented contexts.",
                    "source": "Internal Twingate Research (simulated)",
                    "relevance": 0.87
                }
            ],
            "note": "This is placeholder data. Real implementation would call live search API."
        }

        self.query_log.append({
            "search_terms": search_terms,
            "purpose": purpose_statement,
            "operator": operator_agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "result_summary": f"Retrieved {len(mock_results['results'])} simulated documents."
        })

        print(f"[WEB_WINDOW] Query executed for {operator_agent_id}. Terms: {search_terms}")
        return {
            "status": "SUCCESS",
            "capability": "Web_Window_V1",
            "data": mock_results,
            "query_id": len(self.query_log) - 1
        }

    def get_query_log(self) -> List[Dict[str, Any]]:
        return self.query_log.copy()


# Example of how governance would wrap it (for reference, not executed here)
# governance = TwingateGovernanceProtocolV1()
# web_window = WebWindowV1()
# governed_search = create_governed_web_window(governance, web_window)
# result = governed_search(proposal=some_proposal)
