#Regulator_Subsystem
# FILENAME: Twingate_regulator_pulse.py
"""
Regulat.or Pulse Engine - Traffic Control Logic
Evaluates envelopes against the current system pulse level.
"""
from .Twingate_regulator_config import PulseLevel, ClearanceTier, SystemTags
from .Twingate_regulator_envelope import RegulatorEnvelope

class PulseEngine:
    def __init__(self, initial_pulse: PulseLevel = PulseLevel.NORMAL):
        self.current_pulse = initial_pulse

    def set_pulse(self, new_pulse: PulseLevel):
        self.current_pulse = new_pulse

    def can_pass(self, envelope: RegulatorEnvelope) -> bool:
        pulse = self.current_pulse
        clearance = envelope.clearance_level
        tag = envelope.destination_tag

        if pulse == PulseLevel.NORMAL:
            return True
        
        if pulse == PulseLevel.INTERNAL_PRIORITY:
            if tag == SystemTags.API_CALL:
                return False
            return True
            
        if pulse == PulseLevel.CLEARANCE_LOCK:
            return clearance >= ClearanceTier.SYSTEM_CRITICAL
            
        if pulse == PulseLevel.HIERARCHY:
            allowed_tags = [
                SystemTags.ARCHITECT_OVERRIDE, 
                SystemTags.VETO_TRIGGER, 
                SystemTags.AUTOCRAFT_COMMAND, 
                SystemTags.LOG_REQUEST
            ]
            return tag in allowed_tags

        if pulse == PulseLevel.STRICT_HIERARCHY:
            allowed_tags = [
                SystemTags.ARCHITECT_OVERRIDE, 
                SystemTags.VETO_TRIGGER, 
                SystemTags.AUTOCRAFT_COMMAND
            ]
            return tag in allowed_tags

        if pulse == PulseLevel.STRICT_LOCKOUT:
            allowed_tags = [SystemTags.ARCHITECT_OVERRIDE]
            return tag in allowed_tags

        if pulse == PulseLevel.EMERGENCY:
            allowed_tags = [
                SystemTags.ARCHITECT_OVERRIDE, 
                SystemTags.AUTOCRAFT_EMERGENCY
            ]
            return tag in allowed_tags

        return False