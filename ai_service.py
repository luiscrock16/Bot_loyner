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

def _call_openai_compatible(api_key: str, base_url: str, model: str, messages: List[Dict[str, str]]) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=1024
    )
    return response.choices[0].message.content.strip()

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

    # 1. xAI GROK (Grok de Elon Musk)
    if GROK_API_KEY:
        try:
            model = DEFAULT_MODEL if "grok" in DEFAULT_MODEL else "grok-2-latest"
            reply = await asyncio.to_thread(_call_openai_compatible, GROK_API_KEY, "https://api.x.ai/v1", model, messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "assistant", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            err_str = str(e)
            if "not available in your region" in err_str:
                print("xAI Grok bloqueado por región local. En la nube (Render) sí funcionará.")
            else:
                print(f"Error en xAI Grok: {e}")

    # 2. GROQ (Llama 3.3 70B - Ultra Rápido y gratis en todas las regiones)
    if GROQ_API_KEY:
        try:
            model = "llama-3.3-70b-versatile"
            reply = await asyncio.to_thread(_call_openai_compatible, GROQ_API_KEY, "https://api.groq.com/openai/v1", model, messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "assistant", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error en Groq: {e}")

    # 3. OPENROUTER
    if OPENROUTER_API_KEY:
        try:
            model = "meta-llama/llama-3.3-70b-instruct:free"
            reply = await asyncio.to_thread(_call_openai_compatible, OPENROUTER_API_KEY, "https://openrouter.ai/api/v1", model, messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "assistant", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error en OpenRouter: {e}")

    # 4. OPENAI (ChatGPT)
    if OPENAI_API_KEY:
        try:
            model = "gpt-4o-mini"
            reply = await asyncio.to_thread(_call_openai_compatible, OPENAI_API_KEY, None, model, messages)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "assistant", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error en OpenAI: {e}")

    # 5. GOOGLE GEMINI
    if GEMINI_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_gemini, GEMINI_API_KEY, "gemini-3.8-flash", prompt, history)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error en Gemini: {e}")

    # Búsqueda web si todo lo demás falla
    results = search_service.search_web(prompt, max_results=3)
    if results:
        return search_service.format_search_summary(prompt, results)

    return "No se pudo obtener respuesta de los proveedores de IA configurados."
