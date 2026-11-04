import re
from datetime import datetime, timedelta
from typing import List, Dict
from ddgs import DDGS

def clean_search_query(prompt: str) -> str:
    """Extrae palabras clave limpias y efectivas para los motores de búsqueda."""
    now = datetime.now()
    p = prompt.lower()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

    # Detección específica de qué se celebra hoy o mañana
    if "mañana" in p and any(k in p for k in ["celebra", "dia", "festiv", "efemerid", "santo"]):
        tomorrow = now + timedelta(days=1)
        return f"que se celebra {tomorrow.day} de {meses[tomorrow.month - 1]} efemerides festividades"

    if "hoy" in p and any(k in p for k in ["celebra", "dia", "festiv", "efemerid", "santo"]):
        return f"que se celebra {now.day} de {meses[now.month - 1]} efemerides festividades"

    # Limpiar signos y frases de relleno
    p_clean = re.sub(r"[¿\?!¡,\.]", " ", p)
    fillers = [
        r"\bc[oó]mo quedaron\b", r"\bcu[aá]les fueron\b", r"\bdime\b", r"\bcu[eé]ntame\b",
        r"\bquiero saber\b", r"\bpuedes decirme\b", r"\bde f[uú]tbol\b", r"\bde la\b",
        r"\bde los\b", r"\b[uú]ltim[oa]s?\b", r"\bpor favor\b"
    ]
    for f in fillers:
        p_clean = re.sub(f, " ", p_clean)

    p_clean = " ".join(p_clean.split())

    # Si es deportes o fútbol, asegurar palabras clave
    if any(k in p_clean for k in ["champions", "partido", "liga", "madrid", "barcelona", "futbol"]):
        return f"{p_clean} resultados goles marcadores"

    return p_clean

def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Busca en internet probando noticias primero (si aplica) y luego texto general."""
    clean_q = clean_search_query(query)
    results = []

    try:
        with DDGS() as ddgs:
            # 1. Probar con noticias para deportes o eventos recientes
            try:
                news = list(ddgs.news(clean_q, max_results=max_results))
                if news:
                    for n in news:
                        results.append({
                            "title": n.get("title", ""),
                            "href": n.get("url", n.get("href", "")),
                            "body": n.get("body", "")
                        })
                    return results
            except Exception:
                pass

            # 2. Probar con búsqueda web general
            texts = list(ddgs.text(clean_q, max_results=max_results))
            for t in texts:
                results.append({
                    "title": t.get("title", ""),
                    "href": t.get("href", ""),
                    "body": t.get("body", "")
                })
    except Exception as e:
        print(f"Error en búsqueda: {e}")

    return results

def format_search_summary(query: str, results: List[Dict[str, str]]) -> str:
    if not results:
        return f"No se encontraron resultados para: '{query}'."

    output = [f"🔍 Resultados para: '{query}':\n"]
    for i, r in enumerate(results, 1):
        output.append(f"{i}. {r['title']}\n🔗 {r['href']}\n📝 {r['body']}\n")
    return "\n".join(output)
