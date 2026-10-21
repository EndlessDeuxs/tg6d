# v2_mentorship_receiver.py
import json


class MentorshipReceiver:
    """
    Dedicated gateway for conceptual inputs from Twingate V1.
    Enforces strict, non-executable JSON input.
    """

    def __init__(self):
        print("V2 Mentorship Receiver: Awaiting JSON payloads from V1.")

    def receive_payload(self, raw_input_from_v1: str) -> dict:
        """
        Parses a raw JSON string from V1 into a Python dict.

        Rules:
        - Uses json.loads ONLY.
        - Payload must be a JSON object (maps to Python dict).
        - On failure, returns a structured error concept.
        """
        try:
            conceptual_data = json.loads(raw_input_from_v1)
            if not isinstance(conceptual_data, dict):
                raise ValueError("Payload must be a JSON object.")
            return conceptual_data
        except (json.JSONDecodeError, ValueError) as e:
            return {
                "type": "error_concept",
                "data": raw_input_from_v1,
                "error": f"Strict JSON parsing failed: {str(e)}",
            }
