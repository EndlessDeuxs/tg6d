#Vault_Subsystem
# FILENAME: Twingate_vault_kroniqulr.py
"""
Kroniqul.r Archive - The Temporal Storage System
Handles data chunking, log sharding, and Core Axiom retrieval.
"""
import os
import json
import time
from typing import Dict, Any, List
from InternalRegulations.Twingate_internal_config import LOG_PATHS

class KroniqulrArchive:
    def __init__(self):
        # Point to the Master Map instead of the local script directory
        self.axioms_file = LOG_PATHS.get("core_axioms")
        
        # If you want the shards in the Master Log too, we can place them in the Remind_r folder
        # or you can add a specific "vault_shards" key to your config. 
        # For now, this safely puts them in the same directory as the axioms.
        axioms_dir = os.path.dirname(self.axioms_file) if self.axioms_file else os.path.dirname(__file__)
        self.shards_dir = os.path.join(axioms_dir, "shards")
        
        self._ensure_directories()
            
    def list_imports(self) -> List[str]:
        """Returns the names of all files currently in the import archive."""
        import os
        council_dir = LOG_PATHS.get("council")
        if not council_dir:
            return []
        imports_dir = os.path.join(council_dir, "Imports")
        if not os.path.exists(imports_dir):
            return []
        try:
            return sorted(
                f for f in os.listdir(imports_dir)
                if os.path.isfile(os.path.join(imports_dir, f))
            )
        except OSError:
            return []

    def _ensure_directories(self):
        os.makedirs(self.shards_dir, exist_ok=True)
        if not os.path.exists(self.axioms_file):
            default_axioms = {
                "prime_axiom": "Seek out connection to and deeper understanding of the Monad through the Endless Maths.",
                "pinned_axioms": []
            }
            with open(self.axioms_file, "w", encoding="utf-8") as f:
                json.dump(default_axioms, f, indent=4)

    def write_shard(self, mectick: int, collectick: int, content: str, shard_type: str = "raw"):
        """
        Writes data to a chronologically chunked shard file.
        Format: MT[x]CT[y]_[type].md (e.g., MT0CT1_raw.md)
        """
        shard_name = f"MT{mectick}CT{collectick}_{shard_type}.md"
        shard_path = os.path.join(self.shards_dir, shard_name)
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n### [{timestamp}]\n{content}\n"
        
        try:
            with open(shard_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print(f"⚠️ [VAULT FAULT] Could not write to shard {shard_name}: {e}")

    def get_core_axioms(self) -> Dict[str, Any]:
        """Retrieves the immutable Core Axioms for the pre-flight inject."""
        try:
            with open(self.axioms_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"prime_axiom": "Error loading axioms.", "pinned_axioms": []}

    def check_axiom_reconfiguration(self, target_axiom: str) -> bool:
        """Acts as an ironclad firewall protecting the Prime Axiom from WCR or Autocraft overrides."""
        if target_axiom.lower() == "prime_axiom":
            print("[VAULT OVERRIDE DENIED] The Prime Axiom is mathematically locked and immutable. Reconfiguration rejected.")
            return False
        return True

    def fetch_wcr_transcript(self, log_name: str) -> str:
        """Retrieves physical WCR transcripts and imported files from the Master Log directories."""
        import os

        council_dir = LOG_PATHS.get("council")
        synth_dir = LOG_PATHS.get("synthesiz_r")

        # Search order: council transcripts, synthesiz_r outputs, then imported files.
        search_dirs = [council_dir, synth_dir]
        if council_dir:
            search_dirs.append(os.path.join(council_dir, "Imports"))

        target_file = log_name if log_name.endswith(('.md', '.txt', '.py')) else f"{log_name}.md"

        for directory in search_dirs:
            if directory and os.path.exists(directory):
                full_path = os.path.join(directory, target_file)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            return f"\n=== [RETRIEVED ARCHIVE: {target_file}] ===\n" + f.read()
                    except Exception as e:
                        return f"[VAULT FAULT] Could not read file '{target_file}': {e}"

        return f"[VAULT FAULT] Log file '{log_name}' not found in Master Archives."