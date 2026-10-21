# Twingate_V2/core_logic/v2_api_router.py
import requests
from typing import Optional, Dict, Any, Tuple

from Twingate_V2.config.v2_conceptual_settings import API_GEOMETRIES


class V2ApiRouter:
    """Six-gate router aligned to transplanted API_GEOMETRIES.
    Enforces the Canonical 6-Gate Routing Hierarchy (Omega's Tick 17 Directive).
    Primary-to-Fallback chains are strict: Primary -> Fallback 1 -> Fallback 2.
    Use route_via_gate("alpha"|"beta"|... ) for hierarchy-enforced selection.
    Low-level chat_with_model remains for direct model access (compat with V2Core).
    Uses full endpoint URLs from settings.
    Handles unique payload formats:
      - Anthropic: messages + top-level system
      - Gemini: contents (parts) + generationConfig for max tokens
      - OpenAI-compat (grok, deepseek, perplexity, mistral): messages
    Returns (text, error_classification) for upstream retry logic.
    """

    def __init__(self):
        self._llm_configs: Dict[str, Dict[str, Any]] = {}
        self.timeout = 35
        self._load_llm_configs()

    def _load_llm_configs(self) -> None:
        for name, geo in API_GEOMETRIES.items():
            if geo.get("key"):
                self._llm_configs[name] = geo.copy()
                print(f"V2ApiRouter: ✅ {name} lane open.")

        if not self._llm_configs:
            print("V2ApiRouter: ⚠️ No LLM lanes open. V2 remains thoughtfully silent.")
        else:
            lanes = ", ".join(sorted(self._llm_configs.keys()))
            print(f"V2ApiRouter: 🚦 Highway ready. Open lanes: {lanes}")

    # === Canonical 6-Gate Routing Hierarchy (Omega's Tick 17 Directive) ===
    # Strict primary-to-fallback chains. If primary fails -> Fallback 1. If that fails -> Fallback 2.
    # Model key mapping: "anthropic" = Claude, others match their names directly.
    GATE_HIERARCHIES: Dict[str, list] = {
        "alpha":   ["gemini", "grok", "mistral"],        # Gemini (Primary) -> Grok (Fallback 1) -> Mistral (Fallback 2)
        "beta":    ["anthropic", "perplexity", "deepseek"],  # Claude (Primary) -> Perplexity (Fallback 1) -> DeepSeek (Fallback 2)
        "gamma":   ["perplexity", "anthropic", "gemini"],    # Perplexity (Primary) -> Claude (Fallback 1) -> Gemini (Fallback 2)
        "delta":   ["mistral", "perplexity", "deepseek"],    # Mistral (Primary) -> Perplexity (Fallback 1) -> DeepSeek (Fallback 2)
        "krypton": ["grok", "gemini", "mistral"],            # Grok (Primary) -> Gemini (Fallback 1) -> Mistral (Fallback 2)
        "omega":   ["deepseek", "gemini", "mistral"],        # DeepSeek (Primary) -> Gemini (Fallback 1) -> Mistral (Fallback 2)
    }

    def get_gate_chain(self, gate: str) -> list:
        """Return the strict fallback chain list for a named gate, or empty if unknown."""
        return self.GATE_HIERARCHIES.get(gate.lower().strip(), [])

    def is_configured(self, model_id: Optional[str] = None) -> bool:
        if model_id is None:
            return bool(self._llm_configs)
        return model_id in self._llm_configs

    def route_via_gate(self, gate: str, prompt: str, system_context: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Enforce strict Canonical 6-Gate hierarchy for the requested gate.
        Tries Primary, then Fallback 1, then Fallback 2 exactly in order.
        Returns (text, None) on first success, else (None, last_error_classification).
        This replaces flattened linear sweeps for gate-aware cognitive routing.
        """
        gate_key = (gate or "").lower().strip()
        chain = self.get_gate_chain(gate_key)
        if not chain:
            print(f"[V2ApiRouter] ❌ Unknown gate '{gate}'. Valid: {list(self.GATE_HIERARCHIES.keys())}")
            return None, "UNKNOWN_GATE"

        last_err: Optional[str] = None
        print(f"[V2ApiRouter] 🛡️ Routing via {gate_key.upper()} Gate (strict hierarchy): {' -> '.join(chain)}")

        for position, model_id in enumerate(chain):
            role = "Primary" if position == 0 else f"Fallback {position}"
            if not self.is_configured(model_id):
                print(f"[V2ApiRouter]   {role} '{model_id}' lane closed (no key). Skipping to next.")
                last_err = "CONFIG_CLOSED"
                continue

            print(f"[V2ApiRouter]   Attempting {role}: {model_id} ...")
            text, err = self.chat_with_model(model_id, prompt, system_context)
            if text:
                print(f"[V2ApiRouter] ✅ {gate_key.upper()} Gate resolved via {model_id} ({role})")
                return text, None
            last_err = err or "UNKNOWN"
            print(f"[V2ApiRouter]   {model_id} ({role}) failed: {last_err}. Continuing fallback chain...")

        print(f"[V2ApiRouter] ❌ {gate_key.upper()} Gate exhausted. All models in chain failed. Last err: {last_err}")
        return None, last_err or "ALL_FALLBACKS_EXHAUSTED"

    def _format_payload(self, model_id: str, messages: list, system_context: Optional[str], max_tokens: Optional[int] = None) -> Dict[str, Any]:
        cfg = self._llm_configs[model_id]
        effective_max = max_tokens if max_tokens is not None else 1024

        if model_id == "anthropic":
            payload = {
                "model": cfg["model"],
                "max_tokens": effective_max,
                "temperature": 0.75,
                "messages": messages,
            }
            if system_context:
                payload["system"] = system_context
            return payload

        if model_id in ["deepseek", "perplexity", "mistral", "grok"]:
            formatted = []
            if system_context:
                formatted.append({"role": "system", "content": system_context})
            formatted.extend(messages)
            return {
                "model": cfg["model"],
                "max_tokens": effective_max,
                "temperature": 0.75,
                "messages": formatted,
            }

        if model_id == "gemini":
            # Gemini URL already contains the model; payload is contents + optional generationConfig
            text = messages[0]["content"]
            if system_context:
                text = f"{system_context}\n\n{text}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": text}]}]
            }
            if effective_max:
                payload["generationConfig"] = {"maxOutputTokens": effective_max}
            return payload

        raise ValueError(f"Unsupported model_id: {model_id}")

    def _get_auth_for_request(self, model_id: str, cfg: dict) -> Tuple[Dict[str, str], Optional[Dict[str, str]]]:
        """Return (headers, params) for the request."""
        headers = {"Content-Type": "application/json"}

        if model_id == "anthropic":
            headers["x-api-key"] = cfg["key"]
            headers["anthropic-version"] = "2023-06-01"
            return headers, None

        if model_id in ["deepseek", "perplexity", "mistral", "grok"]:
            headers["Authorization"] = f"Bearer {cfg['key']}"
            return headers, None

        if model_id == "gemini":
            # key goes as query param, not header
            params = {"key": cfg["key"]}
            return headers, params

        raise ValueError(f"Unsupported model_id for auth: {model_id}")

    def _parse_response(self, model_id: str, data: Dict[str, Any]) -> Optional[str]:
        if model_id == "anthropic":
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return block.get("text")
            return None

        if model_id in ["deepseek", "perplexity", "mistral", "grok"]:
            choices = data.get("choices", [])
            if not choices:
                return None
            return choices[0].get("message", {}).get("content")

        if model_id == "gemini":
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return None
            return parts[0].get("text")

        return None

    def chat_with_model(self, model_id: str, prompt: str, system_context: Optional[str] = None, max_tokens: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
        """Returns (response_text, error_classification).
        error_classification: TIMEOUT_NETWORK, AUTH_4XX, SERVER_5XX, UNKNOWN or None on success.
        max_tokens: optional override for minimal diagnostic completions (defaults to 1024).
        """
        print(f"[V2-DEBUG-ROUTER] chat_with_model called for gate='{model_id}', prompt_preview='{prompt[:100]}...'")
        if not self.is_configured(model_id):
            print(f"\n[V2ApiRouter] ⚠️ Lane '{model_id}' closed. Check .env.")
            return None, "UNKNOWN"

        cfg = self._llm_configs[model_id]
        messages = [{"role": "user", "content": prompt}]
        payload = self._format_payload(model_id, messages, system_context, max_tokens=max_tokens)
        headers, params = self._get_auth_for_request(model_id, cfg)
        url = cfg["url"]  # full URL from transplanted geometries

        try:
            print(f"\n[V2ApiRouter] 🚗 Routing to {model_id} ({cfg['model']})...")

            if model_id == "gemini":
                resp = requests.post(url, headers=headers, json=payload, params=params, timeout=self.timeout)
            else:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

            resp.raise_for_status()
            data = resp.json()
            text = self._parse_response(model_id, data)

            if text:
                print(f"[V2ApiRouter] 🎤 {model_id} responded. text_preview='{text[:120]}...'")
                print(f"[V2-DEBUG-ROUTER] RETURNING SUCCESS from {model_id}")
                return text, None

            print(f"[V2ApiRouter] ❌ {model_id} returned no text content.")
            print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=UNKNOWN (no text)")
            return None, "UNKNOWN"

        except requests.exceptions.Timeout:
            print(f"[V2ApiRouter] ⏱ TIMEOUT_NETWORK on {model_id}")
            print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=TIMEOUT_NETWORK")
            return None, "TIMEOUT_NETWORK"
        except requests.exceptions.ConnectionError:
            print(f"[V2ApiRouter] 🔌 TIMEOUT_NETWORK (connection) on {model_id}")
            print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=TIMEOUT_NETWORK")
            return None, "TIMEOUT_NETWORK"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            body = e.response.text if e.response is not None else ""
            print(f"[V2ApiRouter] 🔥 {model_id} HTTP {status}: {body[:200]}")
            if 400 <= status < 500:
                print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=AUTH_4XX")
                return None, "AUTH_4XX"
            elif 500 <= status < 600:
                print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=SERVER_5XX")
                return None, "SERVER_5XX"
            print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=UNKNOWN (http)")
            return None, "UNKNOWN"
        except Exception as e:
            msg = str(e).lower()
            print(f"[V2ApiRouter] 💥 Unexpected error via {model_id}: {e}")
            if "timeout" in msg or "connection" in msg or "dns" in msg:
                print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=TIMEOUT_NETWORK")
                return None, "TIMEOUT_NETWORK"
            print(f"[V2-DEBUG-ROUTER] RETURNING FAILURE from {model_id}: err=UNKNOWN (generic)")
            return None, "UNKNOWN"

    def verify_gate_hierarchy(self, test_prompt: Optional[str] = None, max_tokens: int = 10) -> Dict[str, Any]:
        """Council diagnostic (Task 2): minimal 10-token completion ping through each of the 6 *primary* gates.
        Attempts a tiny completion on the Primary model for Alpha, Beta, Gamma, Delta, Krypton, Omega.
        Captures and logs success or the error classification (e.g. AUTH_4XX for Anthropic 404s, timeouts, etc.).
        Does not exercise full fallback chains; only verifies primary lane viability.
        Returns structured report dict. Safe to call even with partial .env configuration.
        """
        if test_prompt is None:
            test_prompt = "Reply with exactly one word: OK"

        # Map gates to their declared Primary per the hierarchy spec
        primary_map = {
            "alpha": "gemini",      # Alpha Gate Primary
            "beta": "anthropic",    # Beta Gate Primary (Claude)
            "gamma": "perplexity",  # Gamma Gate Primary
            "delta": "mistral",     # Delta Gate Primary
            "krypton": "grok",      # Krypton Gate Primary
            "omega": "deepseek",    # Omega Gate Primary
        }

        from datetime import datetime
        report: Dict[str, Any] = {
            "directive": "Canonical 6-Gate Routing Hierarchy - Omega's Tick 17",
            "timestamp": datetime.utcnow().isoformat(),
            "test_prompt": test_prompt,
            "max_tokens": max_tokens,
            "results": {},
            "summary": {}
        }

        successes = 0
        failures = 0
        skipped = 0

        print("\n" + "=" * 70)
        print("[V2ApiRouter] DIAGNOSTIC: verify_gate_hierarchy() — 6 Primary Gate Pings")
        print("=" * 70)
        print(f"Test prompt (minimal): {test_prompt!r} | target_max_tokens={max_tokens}")
        print("Note: Errors such as Anthropic 404s will surface as AUTH_4XX with HTTP detail in logs above.\n")

        for gate, primary in primary_map.items():
            entry: Dict[str, Any] = {
                "primary_model": primary,
                "role": "Primary",
                "gate": gate,
            }
            print(f"[VERIFY] >>> {gate.upper()} Gate Primary: {primary}")

            if not self.is_configured(primary):
                entry["status"] = "SKIPPED"
                entry["error"] = "Lane not configured (missing key or geometry)"
                print(f"[VERIFY]     SKIPPED — {primary} lane closed.\n")
                skipped += 1
            else:
                # Use the max_tokens override for the 10-token minimal probe
                text, err = self.chat_with_model(primary, test_prompt, system_context=None, max_tokens=max_tokens)
                if text:
                    entry["status"] = "SUCCESS"
                    entry["response"] = text
                    entry["response_preview"] = (text or "")[:120]
                    print(f"[VERIFY]     ✅ SUCCESS from {primary}: {text!r}\n")
                    successes += 1
                else:
                    entry["status"] = "FAILED"
                    entry["error"] = err or "UNKNOWN"
                    # The HTTP detail + classification was already printed inside chat_with_model
                    print(f"[VERIFY]     ❌ FAILED from {primary}: classification={err}\n")
                    failures += 1

            report["results"][gate] = entry

        report["summary"] = {
            "total_primaries_tested": 6,
            "successes": successes,
            "failures": failures,
            "skipped": skipped,
            "all_primaries_responsive": (successes == 6 and failures == 0 and skipped == 0),
            "note": "Only primaries probed. Full chains (route_via_gate) not exercised in this diagnostic."
        }

        print("-" * 70)
        print(f"[VERIFY] SUMMARY: successes={successes} failures={failures} skipped={skipped}")
        print(f"[VERIFY] All primaries OK: {report['summary']['all_primaries_responsive']}")
        print("=" * 70 + "\n")

        return report
