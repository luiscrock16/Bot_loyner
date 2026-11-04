import asyncio
import time
from typing import Dict, List
from openai import OpenAI
from config import (
    GROK_API_KEY,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY
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

    last_error = None
    # 3 intentos con pausas de 1.5s y 2.5s para superar picos 503 de Google
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=formatted,
                config=config
            )
            return resp.text.strip()
        except Exception as e:
            last_error = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise e

    raise last_error

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

    # 1. GROQ (Con Q - console.groq.com) -> Ultra rápido y gratis
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

    # 2. OPENROUTER (openrouter.ai)
    if OPENROUTER_API_KEY:
        try:
            messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
            for h in history[-MAX_HISTORY_TURNS:]:
                messages.append({"role": "assistant" if h["role"] == "model" else "user", "content": h["text"]})
            messages.append({"role": "user", "content": prompt})
            reply = await asyncio.to_thread(_call_openai_compatible, OPENROUTER_API_KEY, "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free", messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Fallo OpenRouter: {e}")

    # 3. GOOGLE GEMINI (gemini-3.8-flash con 3 reintentos)
    if GEMINI_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_gemini, GEMINI_API_KEY, prompt, history)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error en Gemini tras reintentos: {e}")
            if "503" in str(e):
                return (
                    "⚠️ Los servidores gratuitos de Google Gemini están teniendo un pico de saturación (Error 503).\n\n"
                    "👉 Para evitar esperas y saturaciones, te recomiendo usar **Groq** (con Q):\n"
                    "1. Crea tu clave gratis en https://console.groq.com/keys\n"
                    "2. Agrégala en Render como `GROQ_API_KEY`.\n"
                    "¡Responderá de forma instantánea!"
                )
            return f"Hubo un detalle al procesar tu mensaje: {e}"

    return "No hay ninguna clave de IA configurada en el bot."
