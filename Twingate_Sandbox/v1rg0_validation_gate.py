import json

class V1rg0ValidationGate:
    def __init__(self):
        self._task_schema = {
            "required_fields": ["task_id", "timestamp", "status", "payload"],
            "payload_required_fields": ["prompt"],
            "optional_payload_fields": ["model_id", "system", "max_tokens", "design_brief"]
        }
        self._result_schema = {
            "required_fields": ["status", "model_id", "data"],
            "status_values": ["success", "error"]
        }

    def validate_task(self, task: dict) -> dict:
        errors, warnings = [], []
        for field in self._task_schema["required_fields"]:
            if field not in task:
                errors.append(f"Missing required field: '{field}'")
        if "payload" in task:
            payload = task["payload"]
            for field in self._task_schema["payload_required_fields"]:
                if field not in payload:
                    errors.append(f"Missing required payload field: '{field}'")
            if "prompt" in payload and not isinstance(payload["prompt"], str):
                errors.append("Payload field 'prompt' must be a string")
            if "max_tokens" in payload:
                if not isinstance(payload["max_tokens"], int):
                    errors.append("Payload field 'max_tokens' must be an integer")
                elif payload["max_tokens"] < 1 or payload["max_tokens"] > 8192:
                    warnings.append(f"max_tokens ({payload['max_tokens']}) outside [1, 8192]")
            if "model_id" in payload and not isinstance(payload["model_id"], str):
                errors.append("Payload field 'model_id' must be a string")
        if "status" in task:
            valid_statuses = ["received", "in_progress", "completed", "failed"]
            if task["status"] not in valid_statuses:
                warnings.append(f"Non-standard status: {task['status']}")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def validate_result(self, result: dict) -> dict:
        errors, warnings = [], []
        for field in self._result_schema["required_fields"]:
            if field not in result:
                errors.append(f"Missing required result field: '{field}'")
        if "status" in result and result["status"] not in self._result_schema["status_values"]:
            errors.append(f"Status must be one of: {self._result_schema['status_values']}")
        if result.get("status") == "success" and "data" in result and not isinstance(result["data"], dict):
            warnings.append("Data not a structured dict")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def extract_content(self, result: dict, model_id: str) -> str | None:
        if result.get("status") != "success" or not result.get("data"):
            return None
        data = result["data"]
        if "claude" in model_id:
            try:
                return data["content"][0]["text"]
            except (KeyError, IndexError, TypeError):
                return None
        if "openai" in model_id:
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                return None
        if isinstance(data, dict):
            for key in ["response", "text", "output", "message"]:
                if key in data:
                    return str(data[key])
        return None