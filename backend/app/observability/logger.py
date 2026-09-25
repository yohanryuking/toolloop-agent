import logging
import sys

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    """Logger con salida a stdout. Cada ejecución de una herramienta se loguea
    con pares `clave=valor` (conversation_id, tool, duration_ms, error, etc.)
    para poder grepear/filtrar sin depender de una librería extra."""
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
        )
        _CONFIGURED = True
    return logging.getLogger(name)
