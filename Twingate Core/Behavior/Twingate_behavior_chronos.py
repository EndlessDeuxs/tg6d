#Behavior_Subsystem
# FILENAME: Twingate_behavior_chronos.py
"""
Behavior Subsystem – Chronos Engine
Tracks external wall-clock time (the weather) and internal processing time (the pulse).
Conversions: 20 Ticks = 1 CollecTick | 5 CollecTicks = 1 MecTick
"""
import os
import json
import time
import datetime
from typing import Dict, Any

EPOCH_FILE_PATH = "Twingate_behavior_epoch.json"

class ChronosEngine:
    def __init__(self, epoch_file: str = EPOCH_FILE_PATH):
        self.filepath = os.path.join(os.path.dirname(__file__), epoch_file)
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "tick": 0,
            "collectick": 0,
            "mectick": 0,
            "chaotick_variance": 0.0,
            "inception_date": datetime.datetime.now().isoformat()
        }

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            print(f"⚠️ [CHRONOS FAULT] Could not save epoch: {e}")

    def register_depth_exchange_complete(self):
        """Register exactly one Tick after a full Depth Exchange (the entire thought process)."""
        self.advance_tick()

    def advance_tick(self):
        """Internal tick increment. 1 Tick = 1 Full Thought Process / File generated."""
        self.state["tick"] += 1
        
        # 20 Ticks = 1 CollecTick
        if self.state["tick"] >= 20:
            self.state["tick"] = 0
            self.state["collectick"] += 1
            
            # 5 CollecTicks = 1 MecTick (100 Ticks)
            if self.state["collectick"] >= 5:
                self.state["collectick"] = 0
                self.state["mectick"] += 1
                
        self._save()

    def get_chronometrics(self) -> Dict[str, Any]:
        """Returns the full dictionary of current time states."""
        return {
            "wall_clock": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iso_time": datetime.datetime.now().isoformat(),
            "tick": self.state["tick"],
            "collectick": self.state["collectick"],
            "mectick": self.state["mectick"]
        }
        
    def get_current_tick_string(self) -> str:
        """Returns the standardized Tick string for file IDs and context headers."""
        return f"MT{self.state['mectick']:02d}CT{self.state['collectick']:02d}T{self.state['tick']:02d}"

    def get_stamp(self) -> str:
        """Returns the standard Twingate human-readable timestamp."""
        metrics = self.get_chronometrics()
        tick_str = self.get_current_tick_string()
        return f"[{metrics['wall_clock']} | {tick_str}]"