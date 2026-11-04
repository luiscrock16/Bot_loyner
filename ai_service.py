import asyncio
import time
from typing import Dict, List
from openai import OpenAI
from config import (
    GROK_API_KEY,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    DEFAULT_MODEL
)

USER_HISTORIES: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 10

SYSTEM_INSTRUCTION = (
    "Eres un asistente conversacional inteligente, amigable y cercano en Telegram, "
    "exactamente como hablar con ChatGPT o Gemini en la web. "
    "Respondes siempre de forma natural, en español, con explicaciones claras, útiles y humanas. "
    "Recuerdas el contexto de la charla y te adaptas al tono del usuario."
)

def clear_history(user_id: int):
    USER_HISTORIES[user_id] = []

def get_diagnostics() -> Dict[str, str]:
    return {
        "gemini": "Activo (Gemini 3.8 Flash)" if GEMINI_API_KEY else "No configurado",
        "groq": "Activo" if GROQ_API_KEY else "No configurado",
        "grok": "Activo" if GROK_API_KEY else "No configurado"
    }

def _call_gemini(api_key: str, prompt: str, history: List[Dict[str, str]]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    formatted = []
    for h in history[-MAX_HISTORY_TURNS:]:
        role = "user" if h["role"] == "user" else "model"
        formatted.append(types.Content(
            role=role,
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

    # Reintento rápido en caso de pico 503 temporal
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=formatted,
                config=config
            )
            return resp.text.strip()
        except Exception as e:
            if "503" in str(e) and attempt == 0:
                time.sleep(1.5)
                continue
            raise e

def _call_openai_compatible(api_key: str, base_url: str, model: str, messages: List[Dict[str, str]]) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

async def ask_chatbot(user_id: int, prompt: str) -> str:
    history = USER_HISTORIES.setdefault(user_id, [])

    # 1. Si hay clave de GROQ (opcional)
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
            print(f"Fallo Groq: {e}")

    # 2. Motor principal: GOOGLE GEMINI 3.8 FLASH
    if GEMINI_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_gemini, GEMINI_API_KEY, prompt, history)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error en Gemini: {e}")
            if "503" in str(e):
                return "Estoy recibiendo muchas consultas en este instante. Por favor escríbeme de nuevo en unos segundos."
            return f"Hubo un detalle al procesar tu mensaje con la IA: {e}"

    # 3. xAI Grok (si está configurada)
    if GROK_API_KEY:
        try:
            messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
            for h in history[-MAX_HISTORY_TURNS:]:
                messages.append({"role": "assistant" if h["role"] == "model" else "user", "content": h["text"]})
            messages.append({"role": "user", "content": prompt})
            reply = await asyncio.to_thread(_call_openai_compatible, GROK_API_KEY, "https://api.x.ai/v1", "grok-2-latest", messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            return f"Error en Grok: {e}"

    return "No hay ninguna clave de IA configurada en el bot."
