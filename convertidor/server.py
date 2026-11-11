"""Convertidor de documentos a Markdown, con interfaz web para PC y celular.

    python server.py

Luego abrí http://localhost:8000 en la PC, o la dirección que se muestra en la
consola (http://<IP-de-la-PC>:8000) desde el celular conectado al mismo Wi-Fi.
"""

from __future__ import annotations

import hmac
import io
import os
import socket
import sys
import tempfile
import zipfile
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file, send_from_directory

from jobs import EstadoInvalido, JobManager

VERSION = (Path(__file__).resolve().parent / "VERSION").read_text().strip()
BASE = Path(__file__).resolve().parent

EXTENSIONES = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv", ".json", ".xml",
    ".html", ".htm", ".txt", ".epub", ".msg", ".zip",
}  # fmt: skip


def cargar_config(ruta: Path):
    """Lee config.env (líneas CLAVE=valor) sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        v = v.strip().strip('"').strip("'")
        if v:
            os.environ.setdefault(k.strip(), v)


def carpeta_datos_por_defecto() -> Path:
    # En Windows los datos van fuera de la carpeta de la app: así se puede
    # actualizar/reemplazar la app (o tenerla en Google Drive) sin perder nada.
    local = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local:
        return Path(local) / "Convertidor" / "datos"
    return BASE / "datos"


def create_app(manager: JobManager) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_MB", "500")) * 1024 * 1024
    clave = os.environ.get("CLAVE")

    @app.before_request
    def pedir_clave():
        if not clave:
            return None
        auth = request.authorization
        if auth and hmac.compare_digest((auth.password or "").encode(), clave.encode()):
            return None
        return Response(
            "Hace falta la clave.",
            401,
            {"WWW-Authenticate": 'Basic realm="Convertidor"'},
        )

    @app.errorhandler(KeyError)
    def no_existe(_):
        return jsonify(error="Ese archivo ya no existe."), 404

    @app.errorhandler(EstadoInvalido)
    def estado_invalido(e):
        return jsonify(error=str(e)), 409

    @app.errorhandler(413)
    def muy_grande(_):
        return jsonify(error="El archivo es demasiado grande."), 413

    @app.get("/")
    def index():
        return send_from_directory(BASE / "static", "index.html")

    @app.get("/api/trabajos")
    def listar():
        return jsonify(trabajos=manager.listar(), version=VERSION)

    @app.post("/api/subir")
    def subir():
        agregados, rechazados = [], []
        for f in request.files.getlist("archivos"):
            nombre = (f.filename or "archivo").replace("\\", "/").split("/")[-1]
            if Path(nombre).suffix.lower() not in EXTENSIONES:
                rechazados.append({"nombre": nombre, "motivo": "Tipo de archivo no soportado"})
                continue
            agregados.append(manager.agregar(nombre, f.stream))
        return jsonify(agregados=agregados, rechazados=rechazados)

    @app.post("/api/convertir")
    def convertir_todos():
        return jsonify(en_cola=manager.convertir_todos())

    @app.post("/api/trabajos/<job_id>/<accion>")
    def accion(job_id, accion):
        funciones = {
            "convertir": manager.convertir,
            "pausar": manager.pausar,
            "reanudar": manager.reanudar,
            "reiniciar": manager.reiniciar,
        }
        if accion not in funciones:
            abort(404)
        funciones[accion](job_id)
        return jsonify(ok=True)

    @app.delete("/api/trabajos/<job_id>")
    def eliminar(job_id):
        manager.eliminar(job_id)
        return jsonify(ok=True)

    @app.post("/api/eliminar")
    def eliminar_varios():
        ids = (request.get_json(silent=True) or {}).get("ids", [])
        return jsonify(eliminados=manager.eliminar_varios(ids))

    @app.get("/api/trabajos/<job_id>/descargar")
    def descargar(job_id):
        ruta = manager.ruta_salida(job_id)
        nombre = next(t["nombre"] for t in manager.listar() if t["id"] == job_id)
        return send_file(ruta, as_attachment=True, download_name=Path(nombre).stem + ".md")

    @app.get("/api/descargar-todo.zip")
    def descargar_zip():
        tmp = tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024)
        usados: set[str] = set()
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for t in manager.listar():
                if t["estado"] != "listo":
                    continue
                base, nombre, n = Path(t["nombre"]).stem, None, 1
                while nombre is None or nombre in usados:
                    nombre = f"{base}.md" if n == 1 else f"{base} ({n}).md"
                    n += 1
                usados.add(nombre)
                z.write(manager.ruta_salida(t["id"]), nombre)
        tmp.seek(0)
        return send_file(
            io.BytesIO(tmp.read()),
            mimetype="application/zip",
            as_attachment=True,
            download_name="convertidos.zip",
        )

    return app


def ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no envía nada; solo elige la interfaz
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main():
    cargar_config(BASE / "config.env")
    datos = Path(os.environ.get("DATOS_DIR") or carpeta_datos_por_defecto())
    manager = JobManager(
        datos,
        timeout=int(os.environ.get("TIEMPO_MAX_MIN", "10")) * 60,
        copiar_a=os.environ.get("COPIAR_A"),
    )
    manager.iniciar()
    app = create_app(manager)

    host = os.environ.get("HOST", "0.0.0.0")
    puerto = int(os.environ.get("PUERTO", "8000"))
    print(f"Convertidor v{VERSION}")
    print(f"  En esta PC:      http://localhost:{puerto}")
    print(f"  Desde el celular: http://{ip_local()}:{puerto}   (mismo Wi-Fi)")
    print(f"  Datos guardados en: {datos}")
    if os.environ.get("COPIAR_A"):
        print(f"  Copia de resultados en: {os.environ['COPIAR_A']}")
    print("  Para cerrar la app: cerrá esta ventana (o Ctrl+C).\n")

    try:
        try:
            from waitress import serve
        except ImportError:
            app.run(host=host, port=puerto, threaded=True)
        else:
            serve(app, host=host, port=puerto, threads=8, max_request_body_size=app.config["MAX_CONTENT_LENGTH"])
    except OSError as e:
        print(f"\nNo se pudo abrir el puerto {puerto}: {e}")
        print("Seguramente la app ya está abierta (o hay otra versión vieja corriendo).")
        print("Cerrala, o cambiá PUERTO en config.env.")
        sys.exit(1)
    finally:
        manager.detener()


if __name__ == "__main__":
    main()
