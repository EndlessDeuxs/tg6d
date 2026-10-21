# v1rg0_transmission_suit.py
import requests
import json

class V1rg0TransmissionSuit:
    def __init__(self, keychain: 'V1rg0Keychain'):
        self._keychain = keychain

    def _select_endpoint(self, model_id: str) -> dict | None:
        registry = {
            "claude_sonnet_5": {
                "url": "https://api.anthropic.com/v1/messages",
                "headers": {"x-api-key": None, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                "model_name": "claude-3-sonnet-20240229",
                "format_fn": self._format_claude_prompt
            },
            "openai_gpt4": {
                "url": "https://api.openai.com/v1/chat/completions",
                "headers": {"Authorization": None, "content-type": "application/json"},
                "model_name": "gpt-4-turbo",
                "format_fn": self._format_openai_prompt
            }
        }
        return registry.get(model_id)

    def _format_claude_prompt(self, concept: dict) -> dict:
        return {
            "model": self._model_name,
            "max_tokens": concept.get("max_tokens", 1024),
            "system": concept.get("system", "You are P_ROT_OGRAPH_R of the Twingate. Respond in character."),
            "messages": [{"role": "user", "content": concept.get("prompt", "Proceed.")}]
        }

    def _format_openai_prompt(self, concept: dict) -> dict:
        return {
            "model": self._model_name,
            "max_tokens": concept.get("max_tokens", 1024),
            "messages": [
                {"role": "system", "content": concept.get("system", "You are P_ROT_OGRAPH_R of the Twingate. Respond in character.")},
                {"role": "user", "content": concept.get("prompt", "Proceed.")}
            ]
        }

    def transmit(self, model_id: str, concept: dict) -> dict:
        endpoint = self._select_endpoint(model_id)
        if not endpoint:
            return {"status": "error", "error": f"Unknown model_id: {model_id}", "data": None}
        api_key = self._keychain.get_key(model_id)
        if not api_key:
            return {"status": "error", "error": f"No API key found for {model_id}", "data": None}
        headers = endpoint["headers"].copy()
        if "x-api-key" in headers:
            headers["x-api-key"] = api_key
        elif "Authorization" in headers:
            headers["Authorization"] = f"Bearer {api_key}"
        self._model_name = endpoint["model_name"]
        try:
            payload = endpoint["format_fn"](concept)
        except Exception as e:
            return {"status": "error", "error": f"Prompt formatting failed: {str(e)}", "data": None}
        try:
            response = requests.post(endpoint["url"], headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return {"status": "success", "model_id": model_id, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API call failed: {str(e)}", "data": None}
        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"Response parsing failed: {str(e)}", "data": None}