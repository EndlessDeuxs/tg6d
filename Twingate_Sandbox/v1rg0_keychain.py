import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class V1rg0Keychain:
    def __init__(self, master_password: str):
        self._keys: dict[str, str] = {}
        self._salt = b'Twingate_Salt_2026'
        self._cipher = self._generate_cipher(master_password)
        self._load_keys()

    def _generate_cipher(self, password: str) -> Fernet:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=self._salt, iterations=100000)
        return Fernet(base64.urlsafe_b64encode(kdf.derive(password.encode())))

    def _load_keys(self):
        key_file = "v1rg0_keys.enc"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                encrypted_data = f.read()
            try:
                self._keys = json.loads(self._cipher.decrypt(encrypted_data))
            except Exception:
                self._keys = {}
        else:
            self._keys = {}
            self._save_keys()

    def _save_keys(self):
        with open("v1rg0_keys.enc", 'wb') as f:
            f.write(self._cipher.encrypt(json.dumps(self._keys).encode()))

    def add_key(self, key_id: str, key_value: str):
        self._keys[key_id] = key_value
        self._save_keys()

    def get_key(self, key_id: str) -> str | None:
        return self._keys.get(key_id, None)

    def list_keys(self) -> list[str]:
        return list(self._keys.keys())