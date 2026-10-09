"""Configuration constants, color palettes, fonts, and model catalogs."""

THEME_COLORS = {
    "light": {
        "primary_red": "#C62828",
        "hover_red": "#A61F24",
        "light_red_bg": "#FFF1F1",
        "bg_primary": "#F8F9FA",
        "bg_card": "#FFFFFF",
        "bg_subtle": "#F1F3F5",
        "text_primary": "#171717",
        "text_secondary": "#666666",
        "border_color": "#E5E7EB",
        "accent_red": "#C62828",
        "shadow": "rgba(0, 0, 0, 0.05)",
    },
    "dark": {
        "primary_red": "#EF4444",
        "hover_red": "#DC2626",
        "light_red_bg": "rgba(239, 68, 68, 0.15)",
        "bg_primary": "#111315",
        "bg_card": "#1A1D21",
        "bg_elevated": "#22262B",
        "bg_subtle": "#1E2227",
        "text_primary": "#F3F4F6",
        "text_secondary": "#A1A1AA",
        "border_color": "#34383F",
        "accent_red": "#EF4444",
        "shadow": "rgba(0, 0, 0, 0.4)",
    }
}

FONT_PRESETS = {
    "SamsungOne": '"SamsungOne", "Arial", "Helvetica", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    "Arial": 'Arial, Helvetica, sans-serif',
    "JetBrains Mono": '"JetBrains Mono", monospace',
}

# ---------------------------------------------------------------------------
# Primary Model Catalog (One Hardcoded Primary Model Per Provider)
# ---------------------------------------------------------------------------
MODEL_CATALOG = {
    "Google Gemini": {
        "primary_model": "gemini-3.8-flash",
        "models": ["gemini-3.8-flash", "gemini-flash-latest"],
        "description": "Google's Gemini 3.8 Flash high-speed multimodal intelligence.",
        "requires_api_key": True,
        "supports_vision": True
    },
    "OpenAI": {
        "primary_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini"],
        "description": "OpenAI GPT-4o Mini fast, cost-efficient multimodal reasoning.",
        "requires_api_key": True,
        "supports_vision": True
    },
    "DeepSeek": {
        "primary_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "description": "DeepSeek-V3 and DeepSeek-R1 deep reasoning intelligence via api.deepseek.com/v1.",
        "requires_api_key": True,
        "supports_vision": False,
        "base_url": "https://api.deepseek.com/v1"
    },
    "Groq": {
        "primary_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile"],
        "description": "Llama 3.3 70B sub-second inference via Groq LPU engine.",
        "requires_api_key": True,
        "supports_vision": True
    },
    "Ollama": {
        "primary_model": "llama3.2",
        "vision_model": "llava",
        "models": ["llama3.2", "llava", "bakllava"],
        "description": "100% private local execution on your machine via Ollama (using llava for vision).",
        "requires_api_key": False,
        "supports_vision": True,
        "base_url": "http://localhost:11434"
    },
    "Offline Heuristics": {
        "primary_model": "built-in-tf-idf",
        "models": ["built-in-tf-idf"],
        "description": "Pure Python algorithmic analysis with zero external dependencies.",
        "requires_api_key": False,
        "supports_vision": False
    }
}

# Provider to Primary Model Mapping
PROVIDER_PRIMARY_MODELS = {
    "Google Gemini": "gemini-3.8-flash",
    "OpenAI": "gpt-4o-mini",
    "DeepSeek": "deepseek-chat",
    "Groq": "llama-3.3-70b-versatile",
    "Ollama": "llama3.2",
    "Offline Heuristics": "built-in-tf-idf"
}