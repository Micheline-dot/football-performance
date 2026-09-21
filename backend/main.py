from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pathlib import Path
import shutil
import subprocess
import re
import json
import cv2


BASE_DIR = Path(__file__).resolve().parent.parent

YOLO_DIR = BASE_DIR / "Football-Analysis-using-YOLO"
INPUT_DIR = YOLO_DIR / "input_videos"
OUTPUT_DIR = YOLO_DIR / "output_videos"
STUB_DIR = YOLO_DIR / "stubs"

INPUT_VIDEO = INPUT_DIR / "match.mp4"
OUTPUT_AVI = OUTPUT_DIR / "output_video.avi"
OUTPUT_MP4 = OUTPUT_DIR / "output_video.mp4"
METRICS_JSON = OUTPUT_DIR / "metrics.json"

YOLO_PYTHON = YOLO_DIR / ".venv" / "Scripts" / "python.exe"


app = FastAPI(
    title="Football Performance API",
    description="API para análisis de rendimiento futbolístico mediante visión artificial",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STUB_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/resultados",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="resultados"
)


@app.get("/")
def inicio():
    return {
        "sistema": "Football Performance",
        "estado": "activo",
        "mensaje": "API funcionando correctamente"
    }


@app.get("/api/estado")
def estado():
    return {
        "backend": "FastAPI",
        "vision_artificial": "YOLO",
        "tracking": "ByteTrack",
        "estado": "disponible"
    }


def convertir_a_mp4(archivo_avi: Path, archivo_mp4: Path):
    """
    Usa FFmpeg para generar un MP4 H.264 compatible con Chrome.
    """
    comando = [
        "ffmpeg",
        "-y",
        "-i", str(archivo_avi),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(archivo_mp4)
    ]

    proceso = subprocess.run(
        comando,
        capture_output=True,
        text=True
    )

    if proceso.returncode != 0:
        raise RuntimeError(
            f"FFmpeg no pudo convertir el video:\n{proceso.stderr}"
        )

    if not archivo_mp4.exists() or archivo_mp4.stat().st_size == 0:
        raise RuntimeError("FFmpeg no produjo un MP4 válido.")




@app.get("/api/descargar-video")
def descargar_video(nombre: str = "football-performance-analisis"):
    """Descarga el video MP4 procesado como archivo, no como reproducción en el navegador."""
    if not OUTPUT_MP4.exists():
        raise HTTPException(status_code=404, detail="No existe un video analizado para descargar.")

    nombre_limpio = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ_-]+", "_", nombre).strip("_")
    if not nombre_limpio:
        nombre_limpio = "football-performance-analisis"

    return FileResponse(
        path=str(OUTPUT_MP4),
        media_type="video/mp4",
        filename=f"{nombre_limpio}.mp4",
        headers={"Content-Disposition": f'attachment; filename="{nombre_limpio}.mp4"'}
    )


@app.delete("/api/analisis")
def eliminar_analisis():
    """
    Elimina el análisis activo y sus archivos generados.
    """
    archivos = [
        INPUT_VIDEO,
        OUTPUT_AVI,
        OUTPUT_MP4,
        METRICS_JSON,
        STUB_DIR / "track_stubs.pkl",
        STUB_DIR / "camera_movement_stub.pkl",
    ]

    eliminados = 0

    for archivo in archivos:
        if archivo.exists():
            try:
                archivo.unlink()
                eliminados += 1
            except OSError as exc:
                print(f"No se pudo eliminar {archivo}: {exc}")

    return {
        "estado": "eliminado",
        "mensaje": "El análisis actual fue eliminado.",
        "archivos_eliminados": eliminados
    }


@app.post("/api/analizar")
async def analizar_video(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No se recibió ningún video."
        )

    extensiones_validas = {".mp4", ".avi", ".mov", ".mkv"}
    extension = Path(file.filename).suffix.lower()

    if extension not in extensiones_validas:
        raise HTTPException(
            status_code=400,
            detail="Formato no permitido. Use MP4, AVI, MOV o MKV."
        )

    if not YOLO_PYTHON.exists():
        raise HTTPException(
            status_code=500,
            detail=f"No se encontró el entorno de YOLO: {YOLO_PYTHON}"
        )

    try:
        with INPUT_VIDEO.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo guardar el video: {exc}"
        )

    # Limpiar resultados anteriores
    for archivo in (OUTPUT_AVI, OUTPUT_MP4, METRICS_JSON):
        if archivo.exists():
            try:
                archivo.unlink()
            except OSError:
                pass

    # Forzar análisis del video nuevo
    for nombre in ("track_stubs.pkl", "camera_movement_stub.pkl"):
        stub = STUB_DIR / nombre
        if stub.exists():
            try:
                stub.unlink()
            except OSError:
                pass

    try:
        proceso = subprocess.run(
            [str(YOLO_PYTHON), "main.py"],
            cwd=str(YOLO_DIR),
            capture_output=True,
            text=True,
            timeout=1800
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="El análisis superó el tiempo máximo de 30 minutos."
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo iniciar YOLO: {exc}"
        )

    print("===== YOLO STDOUT =====")
    print(proceso.stdout)

    print("===== YOLO STDERR =====")
    print(proceso.stderr)

    if proceso.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="YOLO produjo un error. Revise la terminal del backend."
        )

    if not OUTPUT_AVI.exists():
        raise HTTPException(
            status_code=500,
            detail="YOLO terminó, pero no generó output_video.avi."
        )

    try:
        convertir_a_mp4(OUTPUT_AVI, OUTPUT_MP4)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"El análisis terminó, pero no se pudo preparar el MP4: {exc}"
        )

    metricas = {
        "jugadores_detectados": 0,
        "velocidad_maxima": 0,
        "distancia_maxima": 0,
        "jugadores": []
    }

    if METRICS_JSON.exists():
        try:
            with METRICS_JSON.open("r", encoding="utf-8") as archivo:
                metricas = json.load(archivo)
        except Exception as exc:
            print(f"No se pudo leer metrics.json: {exc}")

    return {
        "estado": "completado",
        "mensaje": "Video analizado correctamente.",
        "video": "/resultados/output_video.mp4",
        "metricas": metricas
    }
