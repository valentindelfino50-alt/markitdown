"""PDF a Markdown: app web sencilla sobre MarkItDown.

Flujo:
  1. Subes PDFs (desde el celular o la PC) -> se guardan en la carpeta Entrada/.
  2. Con un clic se convierten a Markdown -> se guardan en la carpeta Salida/.

Las carpetas Entrada/ y Salida/ viven junto a este archivo, asi que si la
carpeta completa esta en OneDrive, tambien puedes soltar PDFs directamente en
Entrada/ desde la app de OneDrive del celular y aparecen aqui.
"""

import argparse
import os
import re
import socket
import threading
import webbrowser
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from markitdown import MarkItDown

QUI = Path(__file__).resolve().parent
BASE = Path(os.environ.get("PDF2MD_BASE", QUI)).resolve()
ENTRADA = BASE / "Entrada"
SALIDA = BASE / "Salida"
ENTRADA.mkdir(parents=True, exist_ok=True)
SALIDA.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # 300 MB por envio

_lock = threading.Lock()
_trabajo = {"corriendo": False, "total": 0, "hechos": 0, "actual": None, "errores": []}


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def nombre_seguro(nombre: str) -> str:
    """Deja solo el nombre del archivo, sin rutas ni caracteres prohibidos."""
    nombre = Path(nombre.replace("\\", "/")).name
    nombre = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nombre).strip(" .")
    return nombre or "documento.pdf"


def nombre_libre(carpeta: Path, nombre: str) -> str:
    """Si ya existe, agrega ' (2)', ' (3)'... para no pisar archivos."""
    destino = carpeta / nombre
    if not destino.exists():
        return nombre
    base, ext = destino.stem, destino.suffix
    n = 2
    while (carpeta / f"{base} ({n}){ext}").exists():
        n += 1
    return f"{base} ({n}){ext}"


def ruta_md(nombre_pdf: str) -> Path:
    return SALIDA / (Path(nombre_pdf).stem + ".md")


def listar_pdfs():
    pdfs = []
    for p in sorted(ENTRADA.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file() or p.suffix.lower() != ".pdf":
            continue
        md = ruta_md(p.name)
        pdfs.append(
            {
                "nombre": p.name,
                "tam": p.stat().st_size,
                "fecha": p.stat().st_mtime,
                "convertido": md.exists(),
                "md": md.name if md.exists() else None,
            }
        )
    return pdfs


def es_pdf_valido(ruta: Path) -> bool:
    with open(ruta, "rb") as f:
        return b"%PDF" in f.read(1024)


# --------------------------------------------------------------------------
# Conversion (en segundo plano para no bloquear el navegador)
# --------------------------------------------------------------------------
def _convertir(nombres):
    conversor = MarkItDown()
    for nombre in nombres:
        with _lock:
            _trabajo["actual"] = nombre
        try:
            texto = conversor.convert_local(str(ENTRADA / nombre)).markdown
            if not texto.strip():
                raise ValueError("No se encontro texto (puede ser un PDF escaneado).")
            destino = ruta_md(nombre)
            parcial = destino.with_suffix(".md.part")
            parcial.write_text(texto, encoding="utf-8")
            os.replace(parcial, destino)
        except Exception as e:  # noqa: BLE001 - se informa al usuario
            with _lock:
                _trabajo["errores"].append({"nombre": nombre, "error": str(e)})
        finally:
            with _lock:
                _trabajo["hechos"] += 1
    with _lock:
        _trabajo["corriendo"] = False
        _trabajo["actual"] = None


# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
@app.get("/")
def inicio():
    return send_from_directory(QUI / "static", "index.html")


@app.get("/api/estado")
def estado():
    with _lock:
        trabajo = dict(_trabajo, errores=list(_trabajo["errores"]))
    return jsonify(
        pdfs=listar_pdfs(),
        trabajo=trabajo,
        carpeta_entrada=str(ENTRADA),
        carpeta_salida=str(SALIDA),
    )


@app.post("/api/subir")
def subir():
    guardados, rechazados = [], []
    for archivo in request.files.getlist("archivos"):
        nombre = nombre_seguro(archivo.filename or "")
        if not nombre.lower().endswith(".pdf"):
            rechazados.append({"nombre": nombre, "motivo": "No es un PDF"})
            continue
        nombre = nombre_libre(ENTRADA, nombre)
        parcial = ENTRADA / (nombre + ".part")
        archivo.save(parcial)
        if not es_pdf_valido(parcial):
            parcial.unlink(missing_ok=True)
            rechazados.append({"nombre": nombre, "motivo": "El archivo no parece un PDF"})
            continue
        os.replace(parcial, ENTRADA / nombre)
        guardados.append(nombre)
    return jsonify(guardados=guardados, rechazados=rechazados)


@app.post("/api/convertir")
def convertir():
    """Convierte los PDFs indicados, o todos los pendientes si no se indica ninguno."""
    pedidos = (request.get_json(silent=True) or {}).get("archivos")
    existentes = {p["nombre"]: p for p in listar_pdfs()}
    if pedidos:
        nombres = [n for n in pedidos if n in existentes]
    else:
        nombres = [n for n, p in existentes.items() if not p["convertido"]]
    if not nombres:
        return jsonify(error="No hay PDFs pendientes por convertir."), 400
    with _lock:
        if _trabajo["corriendo"]:
            return jsonify(error="Ya hay una conversion en curso."), 409
        _trabajo.update(corriendo=True, total=len(nombres), hechos=0, actual=None, errores=[])
    threading.Thread(target=_convertir, args=(nombres,), daemon=True).start()
    return jsonify(iniciado=len(nombres))


@app.get("/api/md/<path:nombre>")
def obtener_md(nombre):
    if Path(nombre).name != nombre or not nombre.lower().endswith(".md"):
        abort(404)
    descargar = request.args.get("descargar") == "1"
    respuesta = send_from_directory(
        SALIDA,
        nombre,
        mimetype="text/plain; charset=utf-8" if not descargar else "text/markdown",
        as_attachment=descargar,
    )
    return respuesta


# --------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------
def ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # no envia datos; solo elige la interfaz
            return s.getsockname()[0]
    except OSError:
        return "IP-de-tu-PC"


def main():
    ap = argparse.ArgumentParser(description="PDF a Markdown")
    ap.add_argument("--celular", action="store_true",
                    help="Permite entrar desde otros dispositivos de tu red Wi-Fi.")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--no-abrir", action="store_true", help="No abrir el navegador.")
    args = ap.parse_args()

    host = "0.0.0.0" if args.celular else "127.0.0.1"
    print(f"\n  Carpeta de entrada: {ENTRADA}\n  Carpeta de salida:  {SALIDA}\n")
    print(f"  En esta PC:  http://localhost:{args.puerto}")
    if args.celular:
        print(f"  En el celular (misma Wi-Fi):  http://{ip_local()}:{args.puerto}")
        print("  Cualquiera en tu red podra subir archivos mientras este abierto.")
    print("\n  Para cerrar la app, cierra esta ventana o pulsa Ctrl+C.\n")
    if not args.no_abrir:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{args.puerto}")).start()
    app.run(host=host, port=args.puerto, threaded=True)


if __name__ == "__main__":
    main()
