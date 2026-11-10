# PDF a Markdown

App sencilla sobre [MarkItDown](../README.md): subes PDFs y los conviertes a Markdown con un clic, sin escribir código.

```
 Celular / PC ──sube PDF──▶  Entrada/  ──[Convertir]──▶  Salida/  (archivos .md)
```

## Cómo usarla en tu PC

1. Instala **Python 3.13** (o cualquier versión de 3.10 a 3.14) desde <https://www.python.org/downloads/>. **No uses 3.15**: MarkItDown todavía no lo soporta. Si ya tienes una versión más nueva, puedes instalar 3.13 al lado; el lanzador elige la compatible solo.
2. Haz doble clic en:
   - **Windows:** `iniciar.bat`
   - **Mac / Linux:** `./iniciar.sh`
3. La primera vez prepara todo solo (unos minutos, necesita Internet). Después abre el navegador en `http://localhost:8765`.
4. Sube tus PDFs y pulsa **Convertir pendientes**. Los `.md` quedan en la carpeta `Salida/` y también puedes verlos o descargarlos desde la página.

## Usarla con el celular y la PC (carpeta en OneDrive)

Pon esta carpeta completa (`pdf-a-markdown`) dentro de OneDrive. Las carpetas `Entrada/` y `Salida/` se crean junto a la app y se sincronizan solas. Hay dos maneras de subir PDFs desde el celular:

**A) Con la PC apagada o lejos (la más cómoda):** en el celular abre la app de OneDrive, entra a `pdf-a-markdown/Entrada` y sube o guarda ahí tus PDFs (también sirve *Compartir → OneDrive* desde otras apps). Cuando abras la app en la PC, los PDFs ya estarán en la lista; pulsa **Convertir pendientes**. Los `.md` aparecerán en `Salida/`, y desde el celular los ves en OneDrive.

**B) Con la PC encendida y en la misma Wi-Fi:** inicia la app con `iniciar-con-celular.bat` (o `./iniciar.sh --celular`). La ventana muestra una dirección como `http://192.168.1.20:8765`; ábrela en el navegador del celular para subir PDFs y convertir desde ahí.

> **Seguridad:** con `--celular`, cualquier dispositivo de tu red puede subir archivos mientras la app esté abierta. Úsalo solo en redes de confianza (tu casa, no una Wi-Fi pública) y cierra la ventana cuando termines. Sin esa opción, solo tu PC puede entrar.

## Detalles útiles

- Un PDF cuenta como **Convertido** si existe un `.md` con el mismo nombre en `Salida/`. Para volver a convertirlo, usa **Reconvertir**.
- Si subes un PDF con un nombre que ya existe, se guarda como `nombre (2).pdf`; nunca se pisa nada.
- **PDFs escaneados** (imágenes sin texto): la app te avisa que no encontró texto. Para esos hace falta OCR (ver el plugin `markitdown-ocr` en el README principal del repo), que usa un servicio externo de pago.
- El entorno de Python se guarda fuera de la carpeta (`%LOCALAPPDATA%\pdf-a-markdown` en Windows, `~/.local/share/pdf-a-markdown` en Mac/Linux), así OneDrive no sincroniza miles de archivos técnicos. En cada computadora nueva, la primera vez se prepara automáticamente.
- **Error `DLL load failed while importing _multiarray_umath` (numpy) en Windows:** falta o está desactualizado el *Microsoft Visual C++ Redistributable*. Instala la versión x64 desde <https://aka.ms/vs/17/release/vc_redist.x64.exe>, reinicia la PC y vuelve a abrir `iniciar.bat`. Si persiste, ejecuta en cmd: `"%LOCALAPPDATA%\pdf-a-markdown\venv\Scripts\python.exe" -m pip install "numpy<2.3"`.
- Para cambiar el puerto: `iniciar.bat --puerto 9000`.
- Los PDFs se procesan en tu propio equipo; no se envían a ningún servicio externo.
