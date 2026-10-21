import os
from dotenv import load_dotenv
load_dotenv()

# Keys (Loaded from .env)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Hardcoded Known-Working Endpoints & Models
API_GEOMETRIES = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-3-5-sonnet-20240620",
        "key": ANTHROPIC_API_KEY
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
        "model": "gemini-1.5-pro",
        "key": GEMINI_API_KEY
    },
    "grok": {
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-beta",
        "key": GROK_API_KEY
    },
    "deepseek": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "key": DEEPSEEK_API_KEY
    },
    "perplexity": {
        "url": "https://api.perplexity.ai/chat/completions",
        "model": "llama-3.1-sonar-large-128k-chat",
        "key": PERPLEXITY_API_KEY
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-large-latest",
        "key": MISTRAL_API_KEY
    }
}
