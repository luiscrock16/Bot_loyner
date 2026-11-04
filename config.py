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

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-flash-lite-latest")
PORT = int(os.getenv("PORT", "8080"))

# Instrucción del sistema (personalidad y tono del bot)
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Eres un asistente conversacional inteligente, culto y servicial en Telegram. "
    "Respondes en español con explicaciones claras, humanas y bien redactadas. "
    "Te adaptas a las instrucciones que te soliciten."
)
