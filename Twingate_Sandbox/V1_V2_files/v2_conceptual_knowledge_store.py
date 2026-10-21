# v2_conceptual_knowledge_store.py
"""
Purely in-memory conceptual knowledge store for V2.
No persistence, no file/database access.
"""


class V2ConceptualKnowledgeStore:
    def __init__(self):
        self._conceptual_store = {}
        print("V2 Conceptual Knowledge Store: Blank conceptual slate initialized.")

    def add_concept(self, concept_id: str, concept_data):
        """
        Adds or updates a conceptual piece of knowledge in memory.
        """
        self._conceptual_store[concept_id] = concept_data
        print(f"V2 Knowledge Store: Conceptually stored '{concept_id}'.")

    def get_concept(self, concept_id: str):
        """
        Retrieves a conceptual piece of knowledge by ID.
        (Alias for retrieve_concept for compatibility.)
        """
        return self._conceptual_store.get(concept_id)

    def retrieve_concept(self, concept_id: str):
        """
        Retrieves a conceptual piece of knowledge by ID.
        """
        return self.get_concept(concept_id)

    def get_all_concepts(self) -> dict:
        """
        Returns a shallow copy of all conceptual knowledge.
        """
        return self._conceptual_store.copy()

    def get_summary(self) -> str:
        """
        Returns a concise summary of the current conceptual state.
        Used for diagnostics and snapshots.
        """
        if not self._conceptual_store:
            return "No concepts stored yet (blank slate)."
        count = len(self._conceptual_store)
        keys = list(self._conceptual_store.keys())
        key_list = ", ".join(keys[:5]) + ("..." if len(keys) > 5 else "")
        return f"Knowledge store holds {count} concepts: {key_list}."
