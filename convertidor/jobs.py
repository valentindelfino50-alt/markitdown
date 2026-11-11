"""Cola de conversiones.

Cada archivo se convierte en un proceso hijo (ver convertir_worker.py), de modo
que se puede cancelar de verdad: pausar, reiniciar, eliminar o por tiempo máximo.
El estado se guarda en disco (jobs.json) para sobrevivir a cierres de la app.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

SUBIDO = "subido"
EN_COLA = "en_cola"
CONVIRTIENDO = "convirtiendo"
PAUSADO = "pausado"
LISTO = "listo"
ERROR = "error"

BASE = Path(__file__).resolve().parent


class EstadoInvalido(ValueError):
    """La acción no se puede hacer en el estado actual del archivo."""


def _worker_por_defecto(origen: Path, destino: Path) -> list[str]:
    return [sys.executable, str(BASE / "convertir_worker.py"), str(origen), str(destino)]


class JobManager:
    def __init__(self, data_dir, timeout=600, worker_cmd=None, copiar_a=None):
        self.dir = Path(data_dir)
        self.timeout = timeout
        self.worker_cmd = worker_cmd or _worker_por_defecto
        self.copiar_a = Path(copiar_a) if copiar_a else None

        self.subidos = self.dir / "subidos"
        self.salida = self.dir / "salida"
        self.logs = self.dir / "logs"
        for d in (self.subidos, self.salida, self.logs):
            d.mkdir(parents=True, exist_ok=True)
        self._estado_path = self.dir / "jobs.json"
        self._heartbeat_path = self.dir / "heartbeat"

        self._lock = threading.RLock()
        self._jobs: dict[str, dict] = {}
        self._procs: dict[str, subprocess.Popen] = {}
        self._seq = 0
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self._cargar()

    # ------------------------------------------------------------ persistencia
    def _cargar(self):
        try:
            data = json.loads(self._estado_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        for j in data.get("jobs", []):
            self._jobs[j["id"]] = j
        self._seq = max([j.get("orden", 0) for j in self._jobs.values()] + [0]) + 1

        for p in self.salida.glob("*.part"):
            p.unlink(missing_ok=True)

        # Lo que quedó "convirtiendo" se interrumpió al cerrar la app: no hay
        # ningún proceso detrás. Lo dejamos pausado para que lo reanudes a mano.
        for j in self._jobs.values():
            if j["estado"] == CONVIRTIENDO:
                j["estado"] = PAUSADO
                j["error"] = "Se interrumpió al cerrar la app. Tocá Reanudar para volver a intentarlo."
                j["run"] = j.get("run", 0) + 1
            elif not self._origen(j).exists():
                j["estado"] = ERROR
                j["error"] = "No se encontró el archivo subido."
        self._guardar()

    def _guardar(self):
        with self._lock:
            tmp = self._estado_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"jobs": list(self._jobs.values())}, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            os.replace(tmp, self._estado_path)

    # ------------------------------------------------------------------- rutas
    def _origen(self, j) -> Path:
        return self.subidos / f"{j['id']}{j['ext']}"

    def _destino(self, job_id) -> Path:
        return self.salida / f"{job_id}.md"

    def ruta_salida(self, job_id) -> Path:
        with self._lock:
            j = self._jobs.get(job_id)
            if not j:
                raise KeyError(job_id)
            if j["estado"] != LISTO or not self._destino(job_id).exists():
                raise EstadoInvalido("Todavía no hay resultado para descargar.")
            return self._destino(job_id)

    # --------------------------------------------------------------- consultas
    def listar(self):
        ahora = time.time()
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j["creado"])
            return [self._publico(j, ahora) for j in jobs]

    def _publico(self, j, ahora):
        t = None
        if j.get("inicio"):
            if j["estado"] == CONVIRTIENDO:
                t = ahora - j["inicio"]
            elif j.get("fin"):
                t = j["fin"] - j["inicio"]
        return {
            "id": j["id"],
            "nombre": j["nombre"],
            "tamano": j["tamano"],
            "estado": j["estado"],
            "error": j.get("error"),
            "transcurrido": t,
        }

    # ----------------------------------------------------------------- acciones
    def agregar(self, nombre: str, stream) -> dict:
        ext = Path(nombre).suffix.lower()
        job_id = uuid.uuid4().hex[:12]
        job = {
            "id": job_id,
            "nombre": nombre,
            "ext": ext,
            "tamano": 0,
            "estado": SUBIDO,
            "error": None,
            "creado": time.time(),
            "inicio": None,
            "fin": None,
            "orden": 0,
            "run": 0,
        }
        destino = self._origen(job)
        try:
            with open(destino, "wb") as f:
                shutil.copyfileobj(stream, f, 1024 * 1024)
        except Exception:
            destino.unlink(missing_ok=True)
            raise
        job["tamano"] = destino.stat().st_size
        with self._lock:
            self._jobs[job_id] = job
            self._guardar()
            return self._publico(job, time.time())

    def _get(self, job_id):
        j = self._jobs.get(job_id)
        if not j:
            raise KeyError(job_id)
        return j

    def _poner_en_cola(self, j):
        j["estado"] = EN_COLA
        j["error"] = None
        j["inicio"] = j["fin"] = None
        j["orden"] = self._seq
        self._seq += 1
        j["run"] += 1

    def convertir(self, job_id):
        with self._lock:
            j = self._get(job_id)
            if j["estado"] != SUBIDO:
                raise EstadoInvalido("Este archivo ya está en la cola o convertido.")
            self._poner_en_cola(j)
            self._guardar()
        self._wake.set()

    def convertir_todos(self) -> int:
        with self._lock:
            n = 0
            for j in sorted(self._jobs.values(), key=lambda j: j["creado"]):
                if j["estado"] == SUBIDO:
                    self._poner_en_cola(j)
                    n += 1
            self._guardar()
        self._wake.set()
        return n

    def pausar(self, job_id):
        with self._lock:
            j = self._get(job_id)
            if j["estado"] not in (EN_COLA, CONVIRTIENDO):
                raise EstadoInvalido("Solo se puede pausar lo que está en cola o convirtiendo.")
            j["run"] += 1
            self._matar(job_id)
            j["estado"] = PAUSADO
            j["error"] = None
            j["inicio"] = j["fin"] = None
            self._guardar()

    def reanudar(self, job_id):
        with self._lock:
            j = self._get(job_id)
            if j["estado"] != PAUSADO:
                raise EstadoInvalido("Este archivo no está pausado.")
            self._poner_en_cola(j)
            self._guardar()
        self._wake.set()

    def reiniciar(self, job_id):
        with self._lock:
            j = self._get(job_id)
            if j["estado"] == SUBIDO:
                raise EstadoInvalido("Todavía no se convirtió: usá Convertir.")
            self._matar(job_id)
            self._destino(job_id).unlink(missing_ok=True)
            self._poner_en_cola(j)
            self._guardar()
        self._wake.set()

    def eliminar(self, job_id):
        with self._lock:
            j = self._get(job_id)
            j["run"] += 1
            self._matar(job_id)
            del self._jobs[job_id]
            self._guardar()
            for p in (
                self._origen(j),
                self._destino(job_id),
                self.logs / f"{job_id}.log",
            ):
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass  # en Windows puede estar tomado un instante; no es grave

    def eliminar_varios(self, ids) -> int:
        n = 0
        for job_id in ids:
            try:
                self.eliminar(job_id)
                n += 1
            except KeyError:
                pass
        return n

    def _matar(self, job_id):
        proc = self._procs.get(job_id)
        if proc and proc.poll() is None:
            proc.kill()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                pass

    # ---------------------------------------------------------------- ejecución
    def iniciar(self):
        if self._thread:
            return
        self._thread = threading.Thread(target=self._bucle, name="convertidor", daemon=True)
        self._thread.start()

    def detener(self):
        self._stop.set()
        self._wake.set()
        with self._lock:
            for job_id in list(self._procs):
                self._matar(job_id)
        if self._thread:
            self._thread.join(5)

    def _latido(self):
        try:
            self._heartbeat_path.write_text(str(time.time()))
        except OSError:
            pass

    def _bucle(self):
        while not self._stop.is_set():
            self._latido()
            siguiente = self._tomar_siguiente()
            if siguiente is None:
                self._wake.wait(1.0)
                self._wake.clear()
                continue
            try:
                self._ejecutar(*siguiente)
            except Exception as e:  # que un fallo no mate la cola
                self._terminar_con_error(siguiente[0], siguiente[1], f"Error interno: {e}")

    def _tomar_siguiente(self):
        with self._lock:
            cola = [j for j in self._jobs.values() if j["estado"] == EN_COLA]
            if not cola:
                return None
            j = min(cola, key=lambda j: j["orden"])
            j["estado"] = CONVIRTIENDO
            j["inicio"] = time.time()
            j["fin"] = None
            j["error"] = None
            j["run"] += 1
            self._guardar()
            return j["id"], j["run"]

    def _vigente(self, job_id, token):
        j = self._jobs.get(job_id)
        return bool(j) and j["run"] == token and j["estado"] == CONVIRTIENDO

    def _terminar_con_error(self, job_id, token, mensaje):
        with self._lock:
            if self._vigente(job_id, token):
                j = self._jobs[job_id]
                j["estado"] = ERROR
                j["error"] = mensaje
                j["fin"] = time.time()
                self._guardar()

    def _ejecutar(self, job_id, token):
        with self._lock:
            j = self._jobs[job_id]
            origen, destino = self._origen(j), self._destino(job_id)
        destino.unlink(missing_ok=True)

        env = dict(os.environ, PYTHONUTF8="1", CONVERTIDOR_HEARTBEAT=str(self._heartbeat_path))
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW

        log_path = self.logs / f"{job_id}.log"
        timed_out = False
        rc = None
        try:
            with open(log_path, "wb") as log:
                proc = subprocess.Popen(
                    self.worker_cmd(origen, destino),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=env,
                    **kw,
                )
                with self._lock:
                    if self._vigente(job_id, token):
                        self._procs[job_id] = proc
                    else:  # lo pausaron/eliminaron justo mientras arrancaba
                        proc.kill()
                limite = time.monotonic() + self.timeout
                while True:
                    try:
                        rc = proc.wait(timeout=0.5)
                        break
                    except subprocess.TimeoutExpired:
                        self._latido()
                        if time.monotonic() > limite:
                            timed_out = True
                            proc.kill()
                            rc = proc.wait()
                            break
        except OSError as e:
            self._terminar_con_error(job_id, token, f"No se pudo iniciar la conversión: {e}")
            return
        finally:
            with self._lock:
                self._procs.pop(job_id, None)

        with self._lock:
            if not self._vigente(job_id, token):
                # Pausado, reiniciado o eliminado mientras corría: ya se encargó la acción.
                Path(str(destino) + ".part").unlink(missing_ok=True)
                return
            j = self._jobs[job_id]
            j["fin"] = time.time()
            if timed_out:
                j["estado"] = ERROR
                j["error"] = (
                    f"Tardó más de {max(1, round(self.timeout / 60))} min y se canceló. "
                    "Puede ser un PDF muy pesado o dañado; probá Reiniciar."
                )
            elif rc == 0 and destino.exists():
                j["estado"] = LISTO
                j["error"] = None
                self._copiar_a_destino_extra(j, destino)
            else:
                j["estado"] = ERROR
                j["error"] = self._ultimo_error(log_path, rc)
            self._guardar()

    @staticmethod
    def _ultimo_error(log_path: Path, rc) -> str:
        try:
            lineas = [
                l.strip()
                for l in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                if l.strip()
            ]
        except OSError:
            lineas = []
        if lineas:
            return lineas[-1][:400]
        return f"La conversión falló (código {rc})."

    def _copiar_a_destino_extra(self, j, destino: Path):
        """Copia opcional del .md a otra carpeta (p. ej. una carpeta de Google Drive)."""
        if not self.copiar_a:
            return
        try:
            self.copiar_a.mkdir(parents=True, exist_ok=True)
            base = Path(j["nombre"]).stem or j["id"]
            meta = self.copiar_a / f"{base}.md"
            n = 2
            while meta.exists():
                meta = self.copiar_a / f"{base} ({n}).md"
                n += 1
            shutil.copyfile(destino, meta)
        except OSError as e:
            j["error"] = f"Convertido, pero no se pudo copiar a {self.copiar_a}: {e}"
