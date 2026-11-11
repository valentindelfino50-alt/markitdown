import io
import os
import sys
import time
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jobs import (  # noqa: E402
    CONVIRTIENDO, EN_COLA, ERROR, LISTO, PAUSADO, SUBIDO, EstadoInvalido, JobManager,
)

PDF_MINIMO = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 18 Tf 20 50 Td (Hola mundo) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
trailer<</Root 1 0 R/Size 6>>
%%EOF
"""


def worker_falso(codigo: str):
    """Worker de mentira: ejecuta `codigo` con src/dst disponibles."""
    def cmd(origen, destino):
        return [sys.executable, "-c", f"import sys,time\nsrc,dst=sys.argv[1:3]\n{codigo}", str(origen), str(destino)]
    return cmd


ESCRIBE_OK = "open(dst,'w').write('# ok')"
CUELGA = "time.sleep(60)"


def esperar(m, job_id, estados, t=15):
    fin = time.time() + t
    while time.time() < fin:
        e = next(j for j in m.listar() if j["id"] == job_id)["estado"]
        if e in estados:
            return e
        time.sleep(0.05)
    raise AssertionError(f"estado final {e!r}, esperaba {estados}")


@pytest.fixture
def mk(tmp_path):
    creados = []

    def _mk(codigo=ESCRIBE_OK, **kw):
        m = JobManager(tmp_path / "datos", worker_cmd=worker_falso(codigo), **kw)
        m.iniciar()
        creados.append(m)
        return m

    yield _mk
    for m in creados:
        m.detener()


def subir(m, nombre="a.pdf", datos=b"x"):
    return m.agregar(nombre, io.BytesIO(datos))["id"]


def test_flujo_completo(mk):
    m = mk()
    i = subir(m)
    assert m.listar()[0]["estado"] == SUBIDO
    m.convertir(i)
    assert esperar(m, i, {LISTO}) == LISTO
    assert m.ruta_salida(i).read_text() == "# ok"


def test_pausar_mata_el_proceso_y_reanudar_vuelve_a_cola(mk):
    m = mk(CUELGA)
    i = subir(m)
    m.convertir(i)
    esperar(m, i, {CONVIRTIENDO})
    time.sleep(0.5)
    proc = m._procs[i]
    m.pausar(i)
    assert proc.poll() is not None, "el proceso debía morir"
    assert esperar(m, i, {PAUSADO}) == PAUSADO
    time.sleep(1.2)  # no debe volver solo a convertir
    assert m.listar()[0]["estado"] == PAUSADO
    m.reanudar(i)
    assert esperar(m, i, {EN_COLA, CONVIRTIENDO}) in {EN_COLA, CONVIRTIENDO}


def test_la_cola_sigue_con_el_siguiente_si_uno_se_pausa(mk):
    m = mk("open(dst,'w').write('# ok') if not src.endswith('.pdf') else time.sleep(60)")
    a, b = subir(m, "a.pdf"), subir(m, "b.txt")
    m.convertir_todos()
    esperar(m, a, {CONVIRTIENDO})
    m.pausar(a)
    assert esperar(m, b, {LISTO}) == LISTO


def test_reiniciar_un_trabado(mk):
    m = mk(CUELGA)
    i = subir(m)
    m.convertir(i)
    esperar(m, i, {CONVIRTIENDO})
    time.sleep(0.5)
    viejo = m._procs[i]
    m.reiniciar(i)
    assert viejo.poll() is not None
    time.sleep(1.5)
    assert m._procs.get(i) is not None and m._procs[i] is not viejo


def test_tiempo_maximo_marca_error(mk):
    m = mk(CUELGA, timeout=1)
    i = subir(m)
    m.convertir(i)
    assert esperar(m, i, {ERROR}) == ERROR
    assert "se canceló" in m.listar()[0]["error"]


def test_error_muestra_ultima_linea(mk):
    m = mk("print('boom'); sys.exit(1)")
    i = subir(m)
    m.convertir(i)
    esperar(m, i, {ERROR})
    assert m.listar()[0]["error"] == "boom"


def test_eliminar_borra_todo_incluso_en_marcha(mk, tmp_path):
    m = mk(CUELGA)
    i = subir(m)
    m.convertir(i)
    esperar(m, i, {CONVIRTIENDO})
    time.sleep(0.5)
    proc = m._procs[i]
    m.eliminar(i)
    assert proc.poll() is not None
    assert m.listar() == []
    assert list((tmp_path / "datos" / "subidos").iterdir()) == []
    with pytest.raises(KeyError):
        m.eliminar(i)


def test_acciones_invalidas(mk):
    m = mk()
    i = subir(m)
    with pytest.raises(EstadoInvalido):
        m.pausar(i)
    with pytest.raises(EstadoInvalido):
        m.reiniciar(i)
    with pytest.raises(EstadoInvalido):
        m.reanudar(i)


def test_al_reabrir_lo_que_estaba_convirtiendo_queda_pausado(tmp_path):
    m = JobManager(tmp_path / "d", worker_cmd=worker_falso(CUELGA))
    i = subir(m)
    # simulamos un cierre brusco con el trabajo "convirtiendo"
    m._jobs[i]["estado"] = CONVIRTIENDO
    m._guardar()
    m2 = JobManager(tmp_path / "d", worker_cmd=worker_falso(CUELGA))
    j = m2.listar()[0]
    assert j["estado"] == PAUSADO and "interrumpió" in j["error"]


def test_copia_a_carpeta_extra(mk, tmp_path):
    extra = tmp_path / "drive"
    m = mk(copiar_a=extra)
    a, b = subir(m, "informe.pdf"), subir(m, "informe.pdf")
    m.convertir_todos()
    esperar(m, a, {LISTO}); esperar(m, b, {LISTO})
    assert sorted(p.name for p in extra.iterdir()) == ["informe (2).md", "informe.md"]


def test_conversion_real_de_pdf(tmp_path):
    m = JobManager(tmp_path / "d", timeout=120)
    m.iniciar()
    try:
        i = subir(m, "prueba ñandú.pdf", PDF_MINIMO)
        m.convertir(i)
        assert esperar(m, i, {LISTO, ERROR}, 60) == LISTO, m.listar()
        assert "Hola mundo" in m.ruta_salida(i).read_text(encoding="utf-8")
    finally:
        m.detener()


def test_pdf_sin_texto_da_error_claro(tmp_path):
    m = JobManager(tmp_path / "d", timeout=120)
    m.iniciar()
    try:
        i = subir(m, "vacio.pdf", PDF_MINIMO.replace(b"(Hola mundo) Tj", b""))
        m.convertir(i)
        assert esperar(m, i, {LISTO, ERROR}, 60) == ERROR
        assert "escaneado" in m.listar()[0]["error"]
    finally:
        m.detener()


# ------------------------------------------------------------------ servidor
def test_api(tmp_path):
    from server import create_app

    m = JobManager(tmp_path / "d", worker_cmd=worker_falso(ESCRIBE_OK))
    m.iniciar()
    try:
        c = create_app(m).test_client()
        r = c.post("/api/subir", data={"archivos": [(io.BytesIO(b"x"), "uno.pdf"), (io.BytesIO(b"x"), "malo.exe")]},
                   content_type="multipart/form-data")
        assert len(r.json["agregados"]) == 1 and r.json["rechazados"][0]["nombre"] == "malo.exe"
        jid = r.json["agregados"][0]["id"]
        assert c.post("/api/convertir").json["en_cola"] == 1
        esperar(m, jid, {LISTO})
        d = c.get(f"/api/trabajos/{jid}/descargar")
        assert d.data == b"# ok" and "uno.md" in d.headers["Content-Disposition"]
        z = zipfile.ZipFile(io.BytesIO(c.get("/api/descargar-todo.zip").data))
        assert z.namelist() == ["uno.md"]
        assert c.post(f"/api/trabajos/{jid}/pausar").status_code == 409
        assert c.post("/api/trabajos/nope/pausar").status_code == 404
        assert c.delete(f"/api/trabajos/{jid}").status_code == 200
        assert c.get("/api/trabajos").json["trabajos"] == []
    finally:
        m.detener()


def test_clave(tmp_path, monkeypatch):
    from server import create_app

    monkeypatch.setenv("CLAVE", "secreta")
    m = JobManager(tmp_path / "d", worker_cmd=worker_falso(ESCRIBE_OK))
    c = create_app(m).test_client()
    assert c.get("/api/trabajos").status_code == 401
    import base64
    ok = {"Authorization": "Basic " + base64.b64encode(b"x:secreta").decode()}
    assert c.get("/api/trabajos", headers=ok).status_code == 200
