#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, '.')
from Twingate_V2.core_logic.v2_main_conceptual_entry import start_v2_conceptual_process

v2 = start_v2_conceptual_process()
ack_payload = {
    "type": "ACK",
    "message": "V2, we hear you. Your answer is received. Cycle 1 cemented."
}
v2.handle_v1_payload(json.dumps(ack_payload))
print("ACK sent – Cycle 1 should now be CEMENTED.")