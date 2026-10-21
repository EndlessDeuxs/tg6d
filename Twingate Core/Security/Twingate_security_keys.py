#Security_Subsystem
# FILENAME: Twingate_security_keys.py
"""
Security Subsystem – API Key Manager
Single source of truth for cryptographic and API key management.
"""
import json
import os
from typing import Dict, Optional

class KeyManager:
    def __init__(self, keys_file: str = "twingate_keys.json"):
        # Anchor to the Twingate Core root directory to prevent ghost files
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.keys_file = os.path.join(base_dir, keys_file)
        self._keys: Dict[str, str] = {}
        self._load_from_file()

    def _load_from_file(self):
        if os.path.exists(self.keys_file):
            try:
                with open(self.keys_file, "r", encoding="utf-8") as f:
                    self._keys = json.load(f)
            except Exception as e:
                print(f"⚠️ [SECURITY FAULT] Could not load keys: {e}")
        else:
            self._save_to_file()

    def _save_to_file(self):
        try:
            with open(self.keys_file, "w", encoding="utf-8") as f:
                json.dump(self._keys, f, indent=4)
        except Exception as e:
            print(f"⚠️ [SECURITY FAULT] Could not save keys: {e}")

    def get_key(self, provider: str) -> str:
        """Retrieves and actively validates the API key for the requested provider."""
        provider = provider.lower()
        key = self._keys.get(provider)
        
        # --- THE BOUNCER CHECK ---
        # Check if the key is missing, empty, or a default placeholder
        if not key or key.strip() == "" or "placeholder" in key.lower():
            error_msg = f"[ERR-WCR-03] / [SEV-5: CRITICAL]: KEY_AUTH_REJECTED - Missing or invalid API key for provider '{provider}'."
            print(f"[SECURITY FAULT] {error_msg}")
            # Raise strict KeyError so the Bridge catches it as a WCR cascade failure
            raise KeyError(error_msg)
            
        return key

    def set_key(self, service: str, key: str):
        self._keys[service.lower()] = key.strip()
        self._save_to_file()
        print(f" [SECURITY] Key updated for {service.upper()}.")

# Singleton instance for easy import across modules
_global_key_manager = None

def get_key_manager() -> KeyManager:
    global _global_key_manager
    if _global_key_manager is None:
        _global_key_manager = KeyManager()
    return _global_key_manager