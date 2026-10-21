#Vault_Subsystem
# FILENAME: Twingate_vault_krowniqulous.py
"""
K.r.owniqulous - The Horizon Matrix
Manages the Dream.r Board, active goals, decay protocols, and pre-flight payloads.
"""
import os
import json
from typing import Dict, Any, List
from .Twingate_vault_kroniqulr import KroniqulrArchive
from InternalRegulations.Twingate_internal_config import LOG_PATHS

class DreamrBoard:
    def __init__(self):
        # Tether directly to the Master Map!
        self.board_file = LOG_PATHS.get("dreamr_board")
        self.archive = KroniqulrArchive()
        
        # Ensure the directory exists before loading
        if self.board_file:
            os.makedirs(os.path.dirname(self.board_file), exist_ok=True)
            
        self.goals = self._load_board()

        # Strict structural limits for the Dream.r Board
        self.board_limits = {
            "short_term": 7,
            "medium_term": 5,
            "med_long_term": 3,
            "long_term": 2
        }

    def _load_board(self) -> Dict[str, List[Dict[str, Any]]]:
        if os.path.exists(self.board_file):
            try:
                with open(self.board_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "short_term": [],     # Up to 7
            "medium_term": [],    # Up to 5
            "med_long_term": [],  # Up to 3
            "long_term": []       # Up to 2
        }

    def save_board(self):
        with open(self.board_file, "w", encoding="utf-8") as f:
            json.dump(self.goals, f, indent=4)

    def add_goal(self, category: str, goal_data: dict) -> bool:
        """Adds a goal to the specified category ONLY if capacity permits."""
        limit = self.board_limits.get(category, 0)
        current_count = len(self.goals.get(category, []))
        
        if current_count >= limit:
            print(f"[VAULT FAULT] Capacity reached for {category} ({limit} max). Council must drop a goal first.")
            return False
            
        self.goals[category].append(goal_data)
        self.save_board()
        return True

    def evaluate_board_decay(self, current_tick: int) -> None:
        """Evaluates all goals against the Chronos Tick and flags decayed items for council review."""
        board_changed = False
        
        for category, goals in self.goals.items():
            for goal in goals:
                # Skip goals that are already flagged, completed, or dropped
                if goal.get("status") not in ["COMPLETED", "DROPPED", "NEEDS_REVIEW"]:
                    # Check if the goal has exceeded its lifespan
                    if current_tick >= goal.get("decay_tick", float('inf')):
                        goal["status"] = "NEEDS_REVIEW"
                        board_changed = True
                        
        if board_changed:
            self.save_board()

    def generate_preflight_inject(self, current_mectick: int, current_collectick: int, current_tick: int) -> str:
        """
        Compiles the Prime Axiom, Pinned Axioms, and active goals into a single string
        to be injected into the RelayContext at Beat 1.
        """
        axioms = self.archive.get_core_axioms()
        
        inject = f"=== TWINGATE PRE-FLIGHT HORIZON ===\n"
        inject += f"CURRENT CHRONOMETRICS: MecTick {current_mectick} | CollecTick {current_collectick} | Tick {current_tick}\n\n"
        
        inject += f"PRIME AXIOM: {axioms.get('prime_axiom', '')}\n\n"
        
        inject += "ACTIVE DREAM.R GOALS:\n"
        for tier, goal_list in self.goals.items():
            active_goals = [g['description'] for g in goal_list if g.get('status') == 'ACTIVE']
            if active_goals:
                inject += f"- {tier.replace('_', ' ').upper()}:\n"
                for g in active_goals:
                    inject += f"  * {g}\n"
                    
        return inject