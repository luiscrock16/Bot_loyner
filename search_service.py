from typing import List, Dict
from ddgs import DDGS

def search_web(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Busca en internet usando DDGS y retorna una lista de resultados con título, enlace y resumen."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            clean_results = []
            for r in results:
                clean_results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
            return clean_results
    except Exception as e:
        print(f"Error en búsqueda web: {e}")
        return []

def format_search_summary(query: str, results: List[Dict[str, str]]) -> str:
    """Convierte los resultados en un texto estructurado para el usuario o contexto de IA."""
    if not results:
        return f"No se encontraron resultados en la web para: '{query}'."

    output = [f"🔍 Resultados de búsqueda para: '{query}':\n"]
    for i, r in enumerate(results, 1):
        output.append(f"{i}. {r['title']}\n🔗 {r['href']}\n📝 {r['body']}\n")
    return "\n".join(output)
