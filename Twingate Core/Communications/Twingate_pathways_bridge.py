#Communications_Pathways
# FILENAME: Twingate_pathways_bridge.py
"""
Communications Layer – API Bridge
Thin wrapper around API calls. Does NOT route or manage state.
"""
import threading
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

        # UIT2 seam: "off"/"shadow" return `messages` unchanged (same object). "on" (UIT2-03) may return a
        # modified copy, only for UIT2_ON_PAIR and only within the frozen call budget. Never raises.
        messages = self._uit2_seam(request, messages)

        return self._call_api(
            model_config,
            api_key,
            messages,
            request.max_tokens,
            request.temperature,
            request.gate_name,
        )

    # ------------------------------------------------------------------ #
    # UIT2-02: off/shadow switch. Reads UIT2_MODE at call time.           #
    # ------------------------------------------------------------------ #
    _uit2_warned: set = set()

    def _uit2_warn(self, msg: str) -> None:
        if msg not in Bridge._uit2_warned:
            Bridge._uit2_warned.add(msg)
            print(f"[UIT2 WARNING] {msg}")

    def _uit2_seam(self, request: RouterRequest, messages: List[Dict]):
        """Returns the messages to dispatch.
        off: `messages` at once, uit2 not imported. shadow: log only, messages unchanged.
        on (UIT2-03): for the configured pair, within budget, returns a NEW list (sheet appended to the
        system line, uit2-encoded context); every other case behaves as shadow. Never raises."""
        try:
            from InternalRegulations import Twingate_internal_config as _cfg
            mode = getattr(_cfg, "UIT2_MODE", "off")
            if mode == "off":
                return messages
            if mode not in ("shadow", "on"):
                self._uit2_warn(f"unknown UIT2_MODE {mode!r}; treated as 'off'")
                return messages
            if mode == "on":
                new, info = self._uit2_on(request, messages, _cfg)
                self._uit2_shadow(request, new if new is not None else messages, _cfg, mode, info)
                if new is not None:
                    return new
                return messages
            self._uit2_shadow(request, messages, _cfg, mode)
        except Exception as e:
            print(f"[UIT2 SHADOW FAULT] {type(e).__name__}: {e}")
        return messages

    # ------------------------------------------------------------------ #
    # UIT2-03: real "on" for ONE configured (role, gate) pair, behind a   #
    # call budget frozen at first use in this process + a ledger file.    #
    # ------------------------------------------------------------------ #
    _uit2_on_lock = threading.Lock()
    _uit2_on_state = None   # {"frozen": tuple, "used": int, "dead": str|None}; set once per process

    def _uit2_on(self, request: RouterRequest, messages: List[Dict], _cfg):
        """Returns (new_messages | None, info). None = do not apply (off behaviour)."""
        import hashlib
        import os
        import re
        sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
        pair = tuple(getattr(_cfg, "UIT2_ON_PAIR", ()))
        if len(pair) != 2 or str(request.role).upper() != str(pair[0]).upper() or request.gate_name != pair[1]:
            return None, {"on": "not_pair"}
        try:
            from . import uit2
            ctx = request.context if isinstance(request.context, str) else ""
            cap = int(getattr(_cfg, "UIT2_SHADOW_MAX_INPUT_CHARS", 400000))
            if not ctx.strip() or len(ctx) > cap:
                return None, {"on": "refused", "on_reason": "context empty or over the input cap"}
            name = lambda s: (re.sub(r"[^A-Za-z0-9_]", "_", s or "") or "unknown")[:40]
            fields = {"v": uit2.VERSION, "src": name(request.role), "tgt": name(request.gate_name), "conf": 1,
                      "unk": {}, "intent": "inf", "claims": [{"neg": False, "p": [], "text": ctx.strip()}],
                      "cons": [], "when": [], "unless": [], "refs": [], "unsaid": []}
            try:
                enc = uit2.encode(fields)
            except uit2.UIT2Error as e:
                return None, {"on": "refused", "on_reason": f"not encodable: {e}"}
            with open(os.path.join(os.path.dirname(uit2.__file__), "SPEC_SHEET.txt"), encoding="utf-8") as f:
                sheet = f.read()
            if sha(sheet) != getattr(_cfg, "UIT2_ON_SHEET_SHA256", ""):
                return None, {"on": "refused", "on_reason": "SPEC_SHEET.txt sha256 != UIT2_ON_SHEET_SHA256"}
        except Exception as e:
            return None, {"on": "refused", "on_reason": f"{type(e).__name__}: {e}"}
        ok, reason, n = self._uit2_budget_take(request, _cfg)
        if not ok:
            self._uit2_warn(f"'on' refused, off behaviour: {reason}")
            return None, {"on": "refused", "on_reason": reason}
        new = [
            {"role": "system", "content": messages[0]["content"] + "\n\n" + sheet.rstrip("\n")},
            {"role": "user", "content": enc},
        ]
        st = Bridge._uit2_on_state["frozen"]
        return new, {
            "on": "applied", "on_budget_id": st[0], "on_call_n": n, "on_budget_calls": st[1], "on_budget_wcr": st[2]}

    def _uit2_budget_take(self, request: RouterRequest, _cfg):
        """Mechanical stop. The budget (id, calls, WCR, calls/WCR, pair, ledger path) is frozen the first time
        it is consulted in this process; any later change -> 'on' refused until restart. Calls already used under
        the same budget id are read from the ledger at freeze time, so a restart does not reset the count.
        A ledger line is written BEFORE the call is allowed; if it cannot be written, the call is refused."""
        import json
        import os
        from datetime import datetime, timezone
        with Bridge._uit2_on_lock:
            cur = (str(getattr(_cfg, "UIT2_ON_BUDGET_ID", "")), getattr(_cfg, "UIT2_ON_BUDGET_CALLS", 0),
                   getattr(_cfg, "UIT2_ON_BUDGET_WCR", 0), getattr(_cfg, "UIT2_CALLS_PER_WCR", 25),
                   tuple(getattr(_cfg, "UIT2_ON_PAIR", ())), _cfg.LOG_PATHS.get("uit2_on_ledger"))
            st = Bridge._uit2_on_state
            if st is None:
                bid, calls, wcr, per, _pair, ledger = cur
                dead, used = None, 0
                if not bid:
                    dead = "UIT2_ON_BUDGET_ID is empty (no approved budget)"
                elif type(calls) is not int or calls < 1:
                    dead = "UIT2_ON_BUDGET_CALLS must be an int >= 1"
                elif type(per) is not int or per < 1 or not isinstance(wcr, (int, float)) or isinstance(wcr, bool):
                    dead = "UIT2_ON_BUDGET_WCR / UIT2_CALLS_PER_WCR invalid"
                elif calls > wcr * per + 1e-9:
                    dead = f"budget {calls} calls exceeds approved {wcr} WCR x {per} calls/WCR"
                elif not ledger:
                    dead = 'LOG_PATHS has no "uit2_on_ledger" key'
                elif not os.path.isabs(ledger):
                    dead = f"ledger path is not absolute on this OS ({ledger!r}); refusing so the count cannot depend on the cwd"
                else:
                    try:
                        if os.path.exists(ledger):
                            with open(ledger, encoding="utf-8") as f:
                                used = sum(1 for line in f if line.strip() and json.loads(line).get("budget_id") == bid)
                    except Exception as e:
                        dead = f"ledger unreadable: {type(e).__name__}: {e}"
                st = Bridge._uit2_on_state = {"frozen": cur, "used": used, "dead": dead}
            if st["dead"]:
                return False, st["dead"], None
            if cur != st["frozen"]:
                st["dead"] = "budget/pair config changed during the run; 'on' refused until restart"
                return False, st["dead"], None
            if st["used"] >= cur[1]:
                return False, f"budget {cur[0]!r} exhausted ({st['used']}/{cur[1]} calls, {cur[2]} WCR)", None
            try:
                parent = os.path.dirname(cur[5])
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(cur[5], "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                        "budget_id": cur[0], "n": st["used"] + 1, "of": cur[1],
                                        "role": request.role, "gate": request.gate_name}, sort_keys=True) + "\n")
            except Exception as e:
                return False, f"ledger write failed: {type(e).__name__}: {e}", None
            st["used"] += 1
            return True, "", st["used"]

    def _uit2_shadow(self, request: RouterRequest, messages: List[Dict], _cfg, mode: str, extra: Dict = None) -> None:
        import hashlib
        import json
        import os
        import re
        from datetime import datetime, timezone

        sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
        ctx = request.context if isinstance(request.context, str) else ""
        keep = int(getattr(_cfg, "UIT2_SHADOW_LOG_MAX_CHARS", 2000))
        cap = int(getattr(_cfg, "UIT2_SHADOW_MAX_INPUT_CHARS", 400000))
        rec = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mode": mode, "gate": request.gate_name, "role": request.role,
            "src_sha256": sha(ctx), "src_chars": len(ctx),
            # Hash of exactly what goes to provider dispatch (same for off and shadow).
            "req_sha256": sha(json.dumps({"gate": request.gate_name, "messages": messages,
                                          "max_tokens": request.max_tokens, "temperature": request.temperature},
                                         sort_keys=True, ensure_ascii=False)),
            "status": "", "reason": "", "match": False, "exact_source": False,
            "envelope_note": "conf=1 and intent=inf are placeholders: RouterRequest carries no confidence or intent",
        }
        try:
            if not ctx.strip():
                rec.update(status="not_encodable", reason="empty context")
            elif len(ctx) > cap:
                rec.update(status="not_encodable", reason=f"context {len(ctx)} chars > UIT2_SHADOW_MAX_INPUT_CHARS {cap}")
            else:
                from . import uit2   # relative: Communications is already loaded; uit2 itself is stdlib-only
                name = lambda s: (re.sub(r"[^A-Za-z0-9_]", "_", s or "") or "unknown")[:40]
                text = ctx.strip()
                fields = {"v": uit2.VERSION, "src": name(request.role), "tgt": name(request.gate_name), "conf": 1,
                          "unk": {}, "intent": "inf", "claims": [{"neg": False, "p": [], "text": text}],
                          "cons": [], "when": [], "unless": [], "refs": [], "unsaid": []}
                try:
                    enc = uit2.encode(fields)
                except uit2.UIT2Error as e:
                    rec.update(status="not_encodable", reason=str(e))
                else:
                    dec = uit2.decode(enc)
                    ren = uit2.render(dec)
                    rec.update(status="encoded", match=(dec == fields), exact_source=(text == ctx),
                               uit2_sha256=sha(enc), uit2_chars=len(enc), render_sha256=sha(ren), render_chars=len(ren),
                               uit2=enc[:keep], render=ren[:keep], clipped=(len(enc) > keep or len(ren) > keep))
        except Exception as e:
            rec.update(status="error", reason=f"{type(e).__name__}: {e}")

        if extra:
            rec.update(extra)
        path = _cfg.LOG_PATHS.get("uit2_shadow")
        if not path:
            self._uit2_warn('LOG_PATHS has no "uit2_shadow" key; shadow records are dropped')
            return
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")

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