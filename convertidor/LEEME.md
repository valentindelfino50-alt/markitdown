# Convertidor a Markdown (PC + celular)

Convierte PDF, Word, PowerPoint, Excel, etc. a Markdown (`.md`). Corre en tu PC y se usa desde el navegador, tanto en la PC como en el celular.

**Qué trae esta versión**

- **Eliminar** archivos subidos (uno, los terminados o todos).
- **Pausar** una conversión, **Reanudar** y **Reiniciar**. Al pausar o reiniciar se corta de verdad el proceso, no solo se cambia el cartel.
- **Tiempo máximo por archivo** (10 min por defecto). Si un PDF se cuelga, queda en *Error* y la cola sigue con el siguiente.
- Al cerrar y abrir la app ya **no** queda nada "Convirtiendo" para siempre: lo que estaba en marcha pasa a *Pausado* y lo reanudás con un toque.
- Ves cuánto lleva cada conversión, para saber si avanza o está trabada.
- Descargás un `.md` o todos juntos en un `.zip`.

---

## 1. Instalar (primera vez)

1. En GitHub, repo `valentindelfino50-alt/markitdown`, rama `claude/dazzling-cori-va7hr5`: **Code → Download ZIP**. Descomprimilo.
2. Copiá **solo la carpeta `convertidor`** a donde quieras. Puede ser dentro de Google Drive (ej. `Mi unidad\Convertidor`) para tenerla en todos tus dispositivos.
3. Necesitás **Python 3.10 o más nuevo** ([python.org/downloads](https://www.python.org/downloads/)). Al instalarlo, marcá **"Add python.exe to PATH"**.
4. Doble clic en **`iniciar.bat`**. La primera vez descarga los componentes (unos minutos). Si Windows pregunta por el firewall, permití el acceso en **redes privadas**: es lo que deja entrar al celular.
5. Se abre una ventana negra con las direcciones. **Esa ventana es la app: si la cerrás, la app se apaga.**

## 2. Usarla

- **En la PC:** abrí `http://localhost:8000`.
- **Desde el celular:** conectado al **mismo Wi-Fi** que la PC, abrí la dirección que dice *"Desde el celular"* en la ventana negra (algo como `http://192.168.1.25:8000`). Podés agregarla a la pantalla de inicio.
- Subí los archivos, tocá **Convertir**, y cuando digan *Listo* tocá **Descargar**.

La PC tiene que estar encendida y con la app abierta. Fuera de tu Wi-Fi no se llega, salvo que uses algo como [Tailscale](https://tailscale.com) (gratis) en la PC y el celular.

## 3. Drive y celular

- **La app en Drive:** el código (pocos KB) puede vivir en Drive. Los archivos pesados (componentes de Python, PDFs subidos, resultados) se guardan **fuera** de esa carpeta, en `%LOCALAPPDATA%\Convertidor`, para que Drive no sincronice miles de archivos.
- **Resultados en Drive automáticamente:** copiá `config.ejemplo.env` como `config.env` y poné, por ejemplo:

  ```
  COPIAR_A=G:\Mi unidad\Convertidos
  ```

  Cada `.md` terminado se copia ahí y aparece solo en Drive del celular. Eliminar un archivo en la app **no** borra esa copia.
- **Alternativa sin config:** bajá el `.md` (o el `.zip`) desde el navegador del celular y se guarda en Descargas.

## 4. Actualizar la app en la PC

1. **Cerrá la ventana negra** de la app.
2. Descargá de nuevo el ZIP de GitHub (paso 1 de arriba).
3. Copiá **el contenido** de la carpeta `convertidor` nueva **encima** de la que tenés, y elegí **Reemplazar los archivos**.
4. Doble clic en `iniciar.bat`.
5. Al pie de la página tiene que decir la versión nueva (ej. `Versión 1.0.0`).

No perdés nada: tus archivos y resultados están en `%LOCALAPPDATA%\Convertidor` y tu configuración en `config.env`, y ninguno de los dos viene en el ZIP.

**Si venías usando otra versión de la app:** antes de iniciar esta, cerrá la anterior (si quedó colgada: `Ctrl+Shift+Esc` → buscá `python` o la app → *Finalizar tarea*). Si no, esta puede avisar que el puerto 8000 está ocupado. Los archivos que habías subido en la versión anterior no se traen solos: volvé a subirlos.

## 5. Si algo se traba

| Situación | Qué hacer |
|---|---|
| Un archivo lleva muchos minutos "Convirtiendo" | **Pausar** (lo corta y sigue la cola) o **Reiniciar** (lo corta y vuelve a empezar). |
| Dice *Error: Tardó más de 10 min…* | Es un PDF muy pesado o raro. Reiniciá, o subí `TIEMPO_MAX_MIN=30` en `config.env`. |
| *Error: No se encontró texto…* | El PDF es una imagen escaneada: no tiene texto para extraer. |
| Pausé o reinicié y empezó de cero | Es lo esperado: una conversión a medias no se puede retomar donde quedó. |
| El celular no abre la dirección | Revisá que estén en el mismo Wi-Fi y que el firewall permita redes privadas. |
| "No se pudo abrir el puerto 8000" | Ya hay otra copia abierta; cerrala o cambiá `PUERTO` en `config.env`. |

## 6. Configuración (`config.env`, opcional)

Ver `config.ejemplo.env`: `PUERTO`, `TIEMPO_MAX_MIN`, `COPIAR_A`, `CLAVE` (pide clave al abrir la página; útil si tu Wi-Fi no es solo tuyo), `DATOS_DIR`, `MAX_MB`.

## Para desarrolladores

```bash
pip install -r requirements.txt pytest
python -m pytest tests -q
python server.py
```
