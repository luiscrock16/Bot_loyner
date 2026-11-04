import asyncio
from datetime import datetime
import re
from typing import Dict, List
import requests
from config import GEMINI_API_KEY, GROQ_API_KEY
import search_service

USER_HISTORIES: Dict[int, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 8

PATRONES_ACTUALIDAD = [
    r"\bmañana\b", r"\bhoy\b", r"\bayer\b", r"\bpartido(s)?\b", r"\bf[uú]tbol\b",
    r"\bresultado(s)?\b", r"\bmarcador(es)?\b", r"\bnoticia(s)?\b", r"\bprecio\b",
    r"\bclima\b", r"\bcampeonato\b", r"\bchampions\b", r"\bjuego\b", r"\bqui[eé]n gan[oó]\b",
    r"\b[uú]ltim[oa]s?\b", r"\bcelebra\b", r"\befem[eé]ride(s)?\b", r"\bferiado\b"
]

def needs_web_context(prompt: str) -> bool:
    p_lower = prompt.lower()
    for pattern in PATRONES_ACTUALIDAD:
        if re.search(pattern, p_lower):
            return True
    return False

def get_current_date_str() -> str:
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    now = datetime.now()
    return f"{dias[now.weekday()]}, {now.day} de {meses[now.month - 1]} de {now.year}"

def clear_history(user_id: int):
    USER_HISTORIES[user_id] = []

def _call_gemini_rest(api_key: str, prompt_with_context: str, history: List[Dict[str, str]]) -> str:
    fecha_actual = get_current_date_str()
    system_prompt = (
        f"Eres un asistente conversacional inteligente, culto y amigable en Telegram, "
        f"exactamente como hablar con ChatGPT o Gemini en la web. "
        f"La fecha de hoy es: {fecha_actual}. "
        f"Respondes en español con un tono cercano, natural y humano. "
        f"Si se te proporcionan datos recientes de internet, úsalos para redactar una respuesta "
        f"fluida y conversacional con los hechos más relevantes."
    )

    contents = []
    for h in history[-MAX_HISTORY_TURNS:]:
        role = "user" if h["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h["text"]}]})
    contents.append({"role": "user", "parts": [{"text": prompt_with_context}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }

    models = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    last_err = None

    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            r = requests.post(url, json=payload, timeout=12)
            if r.status_code == 200:
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            last_err = f"{r.status_code}: {r.text[:80]}"
        except Exception as e:
            last_err = str(e)
            continue

    raise RuntimeError(last_err)

async def ask_chatbot(user_id: int, prompt: str) -> str:
    history = USER_HISTORIES.setdefault(user_id, [])

    prompt_to_send = prompt
    if needs_web_context(prompt):
        try:
            web_items = await asyncio.to_thread(search_service.search_web, prompt, 3)
            if web_items:
                snippets = "\n".join([f"- {it['title']}: {it['body']}" for it in web_items if it['body']])
                if snippets:
                    prompt_to_send = f"{prompt}\n\n[Datos recientes de internet]:\n{snippets}"
        except Exception as e:
            print(f"Error consultando internet: {e}")

    if GEMINI_API_KEY:
        try:
            reply = await asyncio.to_thread(_call_gemini_rest, GEMINI_API_KEY, prompt_to_send, history)
            history.append({"role": "user", "text": prompt})
            history.append({"role": "model", "text": reply})
            USER_HISTORIES[user_id] = history[-MAX_HISTORY_TURNS * 2:]
            return reply
        except Exception as e:
            print(f"Error generando con Gemini: {e}")
            return f"Lo siento, ocurrió un detalle al conectar con la IA: {e}"

    return "No hay clave de IA configurada en el bot."
