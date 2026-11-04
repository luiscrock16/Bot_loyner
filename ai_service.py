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
    # Modelos oficiales actuales de xAI (grok-2-latest primero)
    models_to_try = ["grok-2-latest", "grok-2", "grok-2-1212"]
    last_err = None

    for m in models_to_try:
        try:
            response = client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_err = e
            continue

    # Si ninguno respondió, obtener detalles del error
    err_body = getattr(last_err, "body", None)
    err_msg = err_body if err_body else str(last_err)
    raise RuntimeError(f"Error xAI: {err_msg}")

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

    # 1. Intentar xAI GROK
    if GROK_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_grok, GROK_API_KEY, messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "assistant", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Fallo xAI Grok: {e}. Intentando proveedor de respaldo...")

    # 2. Respaldo: GOOGLE GEMINI (Si Grok falla o no está)
    if GEMINI_API_KEY:
        try:
            # Probar gemini-2.5-flash o gemini-3.8-flash
            for g_model in ["gemini-2.5-flash", "gemini-3.8-flash"]:
                try:
                    reply = await asyncio.to_thread(_call_gemini, GEMINI_API_KEY, g_model, prompt, history)
                    history.append({"role": "user", "text": prompt})
                    history.append({"role": "model", "text": reply})
                    USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
                    return reply
                except Exception as ge:
                    print(f"Fallo con {g_model}: {ge}")
                    continue
        except Exception as e:
            print(f"Error general en Gemini: {e}")

    # 3. Respaldo: Búsqueda web directa
    results = search_service.search_web(prompt, max_results=3)
    if results:
        return search_service.format_search_summary(prompt, results)

    return (
        "⚠️ Hubo un problema al consultar la IA:\n"
        "• xAI Grok rechazó la llamada (verifica si tienes créditos activos en https://console.x.ai/).\n"
        "• Puedes también agregar tu clave gratuita de Groq (https://console.groq.com/keys) como `GROQ_API_KEY`."
    )
