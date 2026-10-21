#Communications_Pathways
# FILENAME: Twingate_pathways_bridge.py
"""
Communications Layer – API Bridge
Thin wrapper around API calls. Does NOT route or manage state.
"""
import time
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Dict, List, Any

from .Twingate_pathways_config import MODEL_REGISTRY
from .Twingate_pathways_interfaces import RouterRequest, RouterResponse

CIRCUIT_BREAKER_TIMEOUT = 210
CIRCUIT_BREAKER_SEV_TAG = "[SEV-4: CRITICAL]"

MODEL_DISPLAY_NAMES = {
    "claude": "Claude",
    "gemini": "Gemini",
    "deepseek": "DeepSeek",
    "grok": "Grok",
    "perplexity": "Perplexity",
    "mistral": "Mistral",
}


def get_model_display_name(model_key: str) -> str:
    return MODEL_DISPLAY_NAMES.get(model_key.lower(), model_key.title())


def format_circuit_breaker_ui_message(model_key: str) -> str:
    display = get_model_display_name(model_key)
    return (
        f"[ERR-WCR-01] / {CIRCUIT_BREAKER_SEV_TAG}: BRIDGE_TIMEOUT\n"
        f"WCR Cascade Aborted: {display} encountered critical API failure. "
        f"Too much bad vibes to stay in there. Please review logs and try again."
    )


class Bridge:
    """Thin API bridge. One job: call APIs and return responses."""

    def __init__(self, key_manager):
        self.key_manager = key_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Twingate/4.0',
            'Accept': 'application/json'
        })
        self.timeout = CIRCUIT_BREAKER_TIMEOUT

    def call(self, request: RouterRequest) -> RouterResponse:
        model_config = MODEL_REGISTRY.get(request.gate_name)
        if not model_config:
            return RouterResponse(
                success=False,
                content="",
                model_used="none",
                error=f"No config for {request.gate_name}",
            )

        api_key = self.key_manager.get_key(request.gate_name)
        if not api_key:
            return RouterResponse(
                success=False,
                content="",
                model_used="none",
                error=f"No key for {request.gate_name}",
            )

        messages = [
            {"role": "system", "content": f"You are {request.role.upper()} of the Twingate. Respond in character."},
            {"role": "user", "content": request.context}
        ]

        return self._call_api(
            model_config,
            api_key,
            messages,
            request.max_tokens,
            request.temperature,
            request.gate_name,
        )

    def _circuit_breaker_response(self, model_key: str, model_id: str, error: str) -> RouterResponse:
        display = get_model_display_name(model_key)
        return RouterResponse(
            success=False,
            content=format_circuit_breaker_ui_message(model_key),
            model_used=model_id or model_key,
            error=f"{CIRCUIT_BREAKER_SEV_TAG} {display} API failure: {error}",
            circuit_breaker=True,
        )

    def _ping_telemetry(self, model: str, status: str, latency: float) -> None:
        try:
            from Security.Monit_or_telemetry import MonitorTelemetry
            monitor = MonitorTelemetry()
            monitor.log_api_call(model=model, status=status, latency=latency)
        except Exception as e:
            print(f"[TELEMETRY FAULT] Could not ping Monit.or: {e}")

    def _call_api(
        self,
        model_config: Dict,
        api_key: str,
        messages: List[Dict],
        max_tokens: int,
        temperature: float,
        model_key: str,
    ) -> RouterResponse:
        provider = model_config.get("provider", "")
        endpoint = model_config.get("endpoint", "")
        model = model_config.get("primary", "")

        if provider == "anthropic":
            return self._call_anthropic(endpoint, api_key, model, messages, max_tokens, model_key)
        if provider == "google":
            return self._call_gemini(api_key, model, messages, max_tokens, model_key)
        return self._call_openai_compatible(
            endpoint, api_key, model, messages, max_tokens, temperature, model_key
        )

    def _call_anthropic(self, endpoint, api_key, model, messages, max_tokens, model_key):
        system_parts = [msg["content"] for msg in messages if msg["role"] == "system"]
        user_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages if msg["role"] != "system"]

        payload = {"model": model, "max_tokens": max_tokens, "messages": user_messages}
        if system_parts:
            payload["system"] = "\n".join(system_parts)

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        try:
            start_time = time.time()
            resp = self.session.post(
                endpoint, headers=headers, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            latency = time.time() - start_time
            self._ping_telemetry(model_key, "200 OK", latency)
            data = resp.json()
            return RouterResponse(
                success=True,
                content=data.get("content", [{}])[0].get("text", ""),
                model_used=model,
                finish_reason=data.get("stop_reason", ""),
            )
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            latency = time.time() - start_time if 'start_time' in locals() else 0.0
            self._ping_telemetry(model_key, "FAILED/TIMEOUT", latency)
            return self._circuit_breaker_response(model_key, model, str(exc))
        except requests.RequestException as exc:
            latency = time.time() - start_time if 'start_time' in locals() else 0.0
            self._ping_telemetry(model_key, "FAILED/TIMEOUT", latency)
            return self._circuit_breaker_response(model_key, model, str(exc))

    def _call_gemini(self, api_key, model, messages, max_tokens, model_key):
        def _generate():
            import google.genai as genai
            from google.genai import types

            system_text = " ".join([m["content"] for m in messages if m["role"] == "system"])
            user_text = " ".join([m["content"] for m in messages if m["role"] == "user"])
            client = genai.Client(api_key=api_key)
            config = types.GenerateContentConfig(max_output_tokens=max_tokens)
            if system_text:
                config.system_instruction = system_text
            return client.models.generate_content(model=model, contents=user_text, config=config)

        try:
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=1) as pool:
                resp = pool.submit(_generate).result(timeout=self.timeout)
            latency = time.time() - start_time
            self._ping_telemetry(model_key, "200 OK", latency)
            return RouterResponse(
                success=True,
                content=resp.text or "",
                model_used=model,
                finish_reason="stop",
            )
        except FuturesTimeout:
            latency = time.time() - start_time if 'start_time' in locals() else 0.0
            self._ping_telemetry(model_key, "FAILED/TIMEOUT", latency)
            return self._circuit_breaker_response(
                model_key, model, f"Request timed out after {self.timeout} seconds"
            )
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            latency = time.time() - start_time if 'start_time' in locals() else 0.0
            self._ping_telemetry(model_key, "FAILED/TIMEOUT", latency)
            return self._circuit_breaker_response(model_key, model, str(exc))
        except Exception as exc:
            latency = time.time() - start_time if 'start_time' in locals() else 0.0
            self._ping_telemetry(model_key, "FAILED/TIMEOUT", latency)
            if "timeout" in str(exc).lower() or "timed out" in str(exc).lower():
                return self._circuit_breaker_response(model_key, model, str(exc))
            return self._circuit_breaker_response(model_key, model, str(exc))

    def _call_openai_compatible(self, endpoint, api_key, model, messages, max_tokens, temperature, model_key):
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            start_time = time.time()
            resp = self.session.post(
                endpoint, headers=headers, json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
            latency = time.time() - start_time
            self._ping_telemetry(model_key, "200 OK", latency)
            data = resp.json()
            choice = data.get("choices", [{}])[0]
            return RouterResponse(
                success=True,
                content=choice.get("message", {}).get("content", ""),
                model_used=model,
                finish_reason=choice.get("finish_reason", ""),
            )

        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            latency = time.time() - start_time if 'start_time' in locals() else 0.0
            self._ping_telemetry(model_key, "FAILED/TIMEOUT", latency)
            
            # [DIAGNOSTIC UPGRADE] Capture the raw response body from xAI / OpenAI endpoints
            detail = ""
            try:
                # Check if the response object exists locally in the scratchpad scope
                if 'resp' in locals():
                    detail = resp.text
                elif hasattr(exc, 'response') and exc.response is not None:
                    detail = exc.response.text
            except Exception:
                pass  # Failsafe if body read fails
                
            # Append raw JSON response text directly to the circuit breaker log string
            full_error = f"{str(exc)} | Response: {detail}" if detail else str(exc)
            
            return self._circuit_breaker_response(model_key, model, full_error)