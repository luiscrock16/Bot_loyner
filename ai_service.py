import asyncio
from typing import Dict, List
from openai import OpenAI
from config import (
    GROK_API_KEY,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    OPENAI_API_KEY,
    DEFAULT_MODEL
)
import search_service

USER_HISTORIES: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 10

SYSTEM_INSTRUCTION = (
    "Eres un asistente conversacional inteligente, educado y amigable en Telegram. "
    "Respondes siempre en español de forma directa, útil y amena. "
    "Hoy es 4 de noviembre de 2026."
)

def clear_history(user_id: int):
    USER_HISTORIES[user_id] = []

def get_diagnostics() -> Dict[str, str]:
    return {
        "grok": f"Configurada (longitud {len(GROK_API_KEY)})" if GROK_API_KEY else "No configurada",
        "groq": f"Configurada (longitud {len(GROQ_API_KEY)})" if GROQ_API_KEY else "No configurada",
        "gemini": f"Configurada (longitud {len(GEMINI_API_KEY)})" if GEMINI_API_KEY else "No configurada",
        "openai": f"Configurada" if OPENAI_API_KEY else "No configurada",
        "model": DEFAULT_MODEL
    }

def _call_grok(api_key: str, messages: List[Dict[str, str]]) -> str:
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=15.0)
    # Intentar con grok-beta o grok-2
    models_to_try = ["grok-beta", "grok-2", "grok-2-latest"]
    last_err = None
    for m in models_to_try:
        try:
            response = client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_err = e
            # Si el modelo no existe, probar el siguiente
            if "model" in str(e).lower() or "not found" in str(e).lower():
                continue
            raise e
    raise last_err

def _call_gemini(api_key: str, model: str, prompt: str, history: List[Dict[str, str]]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    formatted = []
    for h in history[-MAX_HISTORY_TURNS:]:
        formatted.append(types.Content(
            role=h["role"],
            parts=[types.Part.from_text(text=h["text"])]
        ))
    formatted.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    ))

    config = types.GenerateContentConfig(
        temperature=0.7,
        system_instruction=SYSTEM_INSTRUCTION
    )
    resp = client.models.generate_content(
        model=model,
        contents=formatted,
        config=config
    )
    return resp.text.strip()

async def ask_chatbot(user_id: int, prompt: str) -> str:
    history = USER_HISTORIES.setdefault(user_id, [])

    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    for h in history[-MAX_HISTORY_TURNS:]:
        role = "assistant" if h["role"] in ["model", "assistant"] else "user"
        messages.append({"role": role, "content": h["text"]})
    messages.append({"role": "user", "content": prompt})

    # 1. xAI GROK
    if GROK_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_grok, GROK_API_KEY, messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "assistant", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            err_str = str(e)
            print(f"Error llamando a xAI Grok: {err_str}")
            return f"⚠️ Error al conectar con xAI Grok: {err_str}\n\nRevisa si la clave tiene créditos activos o permisos en https://console.x.ai/"

    # 2. GOOGLE GEMINI (Si no hay Grok o falla)
    if GEMINI_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_gemini, GEMINI_API_KEY, "gemini-3.8-flash", prompt, history)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                return (
                    "⚠️ Los servidores de Google Gemini están temporalmente saturados (Error 503).\n\n"
                    "👉 Asegúrate de agregar la clave de Grok en Render en la pestaña 'Environment' con el nombre exacto: `GROK_API_KEY`."
                )
            return f"Error en Gemini: {e}"

    # Si no hay ninguna clave detectada en el entorno
    return (
        "🤖 No se detectó ninguna API Key en las variables de entorno de Render.\n\n"
        "Ve a Render > Environment y agrega:\n"
        "`GROK_API_KEY` con tu clave de xAI."
    )
