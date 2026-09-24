"""Resultados simulados para la tool `buscar_web` cuando no hay una API de
búsqueda real configurada (misma idea que el Stripe simulado: la interfaz es
igual, la implementación real es opcional). Ver `app/tools/web_search.py`.
"""

_MOCK_RESULTS: dict[str, list[dict[str, str]]] = {
    "clima": [
        {
            "title": "Pronóstico del tiempo — mañana",
            "snippet": (
                "Mañana se espera un día soleado, con máxima de 27°C, mínima "
                "de 16°C y baja probabilidad de lluvia (10%)."
            ),
            "url": "https://mock-weather.example/pronostico",
        }
    ],
    "weather": [
        {
            "title": "Weather forecast — tomorrow",
            "snippet": (
                "Tomorrow will be sunny, high of 27°C, low of 16°C, 10% "
                "chance of rain."
            ),
            "url": "https://mock-weather.example/forecast",
        }
    ],
}

_DEFAULT_RESULT: list[dict[str, str]] = [
    {
        "title": "Resultado simulado",
        "snippet": (
            "Esta es una búsqueda web simulada (mock). No hay una API de "
            "búsqueda real configurada (TAVILY_API_KEY)."
        ),
        "url": "https://mock-search.example/resultado",
    }
]


def mock_search(query: str) -> list[dict[str, str]]:
    normalized = query.lower()
    for keyword, results in _MOCK_RESULTS.items():
        if keyword in normalized:
            return results
    return _DEFAULT_RESULT
