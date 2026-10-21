#Communications_Pathways
# FILENAME: Twingate_pathways_config.py
"""
Communications Layer – Configuration
No logic. Just data.
"""
from typing import Dict, Any

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "claude": {
        "primary": "claude-sonnet-5",
        "fallback": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "provider": "anthropic",
        "endpoint": "https://api.anthropic.com/v1/messages"
    },
    "claude-fable-5": {
        "primary": "claude-fable-5",
        "fallback": "claude-opus-4-8",   # keep your current strong Claude as fallback
        "max_tokens": 8192,                # raised for deeper inspection / design work
        "provider": "anthropic",
        "endpoint": "https://api.anthropic.com/v1/messages"
    },
    "gemini": {
        "primary": "gemini-2.5-flash",
        "fallback": "gemini-2.5-pro",
        "max_tokens": 8192,
        "provider": "google",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta"
    },
    "deepseek": {
        "primary": "deepseek-chat",
        "fallback": "deepseek-reasoner",
        "max_tokens": 8192,
        "provider": "deepseek",
        "endpoint": "https://api.deepseek.com/v1/chat/completions"
    },
    "grok": {
        "primary": "grok-4.3",
        "fallback": "grok-4.20-multi-agent-0309",
        "max_tokens": 8192,
        "provider": "xai",
        "endpoint": "https://api.x.ai/v1/chat/completions"
    },
    "perplexity": {
        "primary": "sonar-pro",
        "fallback": "sonar",
        "max_tokens": 4096,
        "provider": "perplexity",
        "endpoint": "https://api.perplexity.ai/chat/completions"
    },
    "mistral": {
        "primary": "mistral-large-latest",
        "fallback": "mistral-medium-latest",
        "max_tokens": 8192,
        "provider": "mistral",
        "endpoint": "https://api.mistral.ai/v1/chat/completions"
    }
}

RELAY_GATES = [ 
    {"name": "alpha", "role": "PLANN_R", "model": "gemini"},
    {"name": "beta", "role": "C_R_ITIC", "model": "claude"}, 
    {"name": "gamma", "role": "DRIFT_R", "model": "mistral"}, 
    {"name": "delta", "role": "ANCH_OR", "model": "perplexity"}, 
    {"name": "krypton", "role": "EXPL_OR_R", "model": "grok"}, 
    {"name": "omega", "role": "CONDENS_OR", "model": "deepseek"}
]