#Regulator_Subsystem
# FILENAME: Twingate_regulator_bus.py
"""
Regulat.or Event Bus - The Core Message Broker
Queues, evaluates, and routes envelopes to subscribed functions.
"""
from typing import List, Callable, Dict
from .Twingate_regulator_envelope import RegulatorEnvelope
from .Twingate_regulator_pulse import PulseEngine
from .Twingate_regulator_config import SystemTags

class RegulatorBus:
    def __init__(self, pulse_engine: PulseEngine):
        self.pulse_engine = pulse_engine
        self.queue: List[RegulatorEnvelope] = []
        self.held_queue: List[RegulatorEnvelope] = []
        self.handlers: Dict[SystemTags, List[Callable]] = {tag: [] for tag in SystemTags}

    def subscribe(self, tag: SystemTags, handler: Callable):
        """Register a function to listen for a specific tag."""
        if handler not in self.handlers[tag]:
            self.handlers[tag].append(handler)

    def publish(self, envelope: RegulatorEnvelope):
        """Submit an envelope to the bus."""
        self.queue.append(envelope)
        # Sort by priority_id (higher integer means higher urgency)
        self.queue.sort(key=lambda x: x.priority_id, reverse=True)

    def process_queue(self):
        """Evaluate all queued envelopes against the current pulse."""
        # Re-integrate held items to see if the pulse has changed
        self.queue.extend(self.held_queue)
        self.held_queue.clear()
        
        self.queue.sort(key=lambda x: x.priority_id, reverse=True)

        unprocessed = []
        for envelope in self.queue:
            if self.pulse_engine.can_pass(envelope):
                self._dispatch(envelope)
            else:
                # Pulse rejected it. Hold it for the next cycle.
                self.held_queue.append(envelope)
        
        self.queue = unprocessed

    def _dispatch(self, envelope: RegulatorEnvelope):
        """Deliver the envelope to all subscribed handlers."""
        handlers = self.handlers.get(envelope.destination_tag, [])
        for handler in handlers:
            try:
                handler(envelope)
            except Exception as e:
                print(f"Error handling envelope {envelope.envelope_id}: {e}")