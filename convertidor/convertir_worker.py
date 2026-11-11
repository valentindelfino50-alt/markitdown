"""Convierte UN archivo a Markdown en un proceso aparte.

Uso: python convertir_worker.py <origen> <destino.md>

Corre como proceso hijo del servidor para poder matarlo si se cuelga
(pausar, reiniciar, eliminar o tiempo máximo excedido).

Códigos de salida: 0 = ok, 3 = sin texto, 4 = el servidor dejó de responder,
cualquier otro = error (el mensaje queda en la última línea de stderr).
"""

import os
import sys
import threading
import time

HEARTBEAT = os.environ.get("CONVERTIDOR_HEARTBEAT")
HEARTBEAT_MAX_EDAD = 20  # segundos sin señal del servidor => salir


def _vigilar_servidor():
    """Si el servidor muere de golpe, este proceso no debe quedar huérfano."""
    while True:
        time.sleep(2)
        try:
            if time.time() - os.path.getmtime(HEARTBEAT) > HEARTBEAT_MAX_EDAD:
                os._exit(4)
        except OSError:
            os._exit(4)


def main():
    if len(sys.argv) != 3:
        print("Uso: convertir_worker.py <origen> <destino.md>", file=sys.stderr)
        return 2
    origen, destino = sys.argv[1], sys.argv[2]

    if HEARTBEAT:
        threading.Thread(target=_vigilar_servidor, daemon=True).start()

    from markitdown import MarkItDown

    texto = MarkItDown(enable_plugins=False).convert(origen).text_content
    if not texto or not texto.strip():
        print(
            "No se encontró texto en el documento (¿es un PDF escaneado, solo imágenes?).",
            file=sys.stderr,
        )
        return 3

    parcial = destino + ".part"
    with open(parcial, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    os.replace(parcial, destino)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # el servidor muestra la última línea de stderr
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
