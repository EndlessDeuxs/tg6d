#Behavior_Subsystem
# FILENAME: Twingate_behavior_kaleidoscope.py
"""
Behavior Subsystem – Emotional Kaleidoscope (EK)
Manages the shifting tones, moods, and coherence/variance vectors of the WCR loop.
"""
import random
from typing import Dict

KALEIDOSCOPE_MATRIX = {
    "Momentum":  {"tone": "Urgent",        "mood": "Restless"},
    "Rigor":     {"tone": "Analytical",    "mood": "Critical"},
    "Variance":  {"tone": "Eccentric",     "mood": "Expansive"},
    "Gravity":   {"tone": "Grounded",      "mood": "Focused"},
    "Horizon":   {"tone": "Philosophical", "mood": "Harmonious"},
    "Coherence": {"tone": "Reflective",    "mood": "Synthesizing"}
}

class EmotionalKaleidoscope:
    def __init__(self):
        self.matrix = KALEIDOSCOPE_MATRIX
        self.current_state = {"tone": "Grounded", "mood": "Focused"} # Safe fallback

    def calculate_state_from_tensor(self, mood_tensor: dict) -> dict:
        """
        Translates the mathematical Mood Tensor from ÆTHE.R.NUL
        into actionable persona constraints for the WCR loop.
        """
        if not mood_tensor:
            return self.current_state

        # Sort the physics nodes by their tensor weight (highest first)
        sorted_nodes = sorted(mood_tensor.items(), key=lambda item: item[1], reverse=True)

        # Extract the top two dominant forces
        primary_node = sorted_nodes[0][0]
        secondary_node = sorted_nodes[1][0]

        # Primary dictates Tone, Secondary dictates Mood
        active_tone = self.matrix[primary_node]["tone"]
        active_mood = self.matrix.get(secondary_node, self.matrix[primary_node])["mood"]

        self.current_state = {
            "tone": active_tone,
            "mood": active_mood,
            "primary_driver": primary_node,
            "secondary_driver": secondary_node,
            "hud_readout": f"[{active_tone} Tone | {active_mood} Mood]"
        }

        return self.current_state

    def shift(self):
        """Rolls a new emotional state for the next cycle."""
        self.current_state = self._roll_state()

    def get_mood_reader(self) -> str:
        """Returns the formatted HUD injection string."""
        s = self.current_state
        return f"[EK MOOD READER] Tone: {s['tone']} | Mood: {s['mood']} | Coherence: {s['coherence']} | Variance: {s['variance']} | Velocity: {s['velocity']}"