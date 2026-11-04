import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9183735927:AAGAchlWMGA65pTUs5uvkH5PnUaf0ui4CrQ")

# Proveedores de IA
GROK_API_KEY = os.getenv("GROK_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "grok-2-latest")
PORT = int(os.getenv("PORT", "8080"))
