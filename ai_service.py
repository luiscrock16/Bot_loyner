import asyncio
from typing import Dict, List
import requests
from openai import OpenAI
from config import (
    GROK_API_KEY,
    GROQ_API_KEY,
    GEMINI_API_KEY
)

USER_HISTORIES: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 10

SYSTEM_INSTRUCTION = (
    "Eres un asistente conversacional inteligente, amigable y cercano en Telegram, "
    "exactamente como hablar con ChatGPT o Gemini en la web. "
    "Respondes siempre de forma natural, en español, con explicaciones claras, útiles y humanas. "
    "Recuerdas el contexto de la charla y te adaptas al tono del usuario."
)

GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

def clear_history(user_id: int):
    USER_HISTORIES[user_id] = []

def _call_gemini_rest(api_key: str, prompt: str, history: List[Dict[str, str]]) -> str:
    """Llama a la API REST de Google Gemini probando los modelos de alta disponibilidad."""
    contents = []
    for h in history[-MAX_HISTORY_TURNS:]:
        role = "user" if h["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h["text"]}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }

    last_error = None
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            r = requests.post(url, json=payload, timeout=12)
            if r.status_code == 200:
                data = r.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            elif r.status_code == 503:
                last_error = "503 Saturado"
                continue
            else:
                last_error = f"{r.status_code}: {r.text[:100]}"
                continue
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"No se pudo conectar a los servidores de Gemini: {last_error}")

def _call_openai_compatible(api_key: str, base_url: str, model: str, messages: List[Dict[str, str]]) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=12.0)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

async def ask_chatbot(user_id: int, prompt: str) -> str:
    history = USER_HISTORIES.setdefault(user_id, [])

    # 1. GROQ (Si está configurado y accesible)
    if GROQ_API_KEY:
        try:
            messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
            for h in history[-MAX_HISTORY_TURNS:]:
                messages.append({"role": "assistant" if h["role"] == "model" else "user", "content": h["text"]})
            messages.append({"role": "user", "content": prompt})
            reply = await asyncio.to_thread(_call_openai_compatible, GROQ_API_KEY, "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Fallo Groq: {e}. Probando Gemini...")

    # 2. GOOGLE GEMINI (Modelos de alta disponibilidad sin 503)
    if GEMINI_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_gemini_rest, GEMINI_API_KEY, prompt, history)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error en Gemini REST: {e}")
            return f"Lo siento, ocurrió un detalle al conectar con la IA: {e}"

    return "No hay ninguna clave de IA configurada en el bot."
