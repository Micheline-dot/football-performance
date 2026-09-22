FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Dependencias del sistema necesarias para OpenCV y FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python para la nube
COPY backend/requirements-cloud.txt /app/requirements-cloud.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements-cloud.txt

# Backend
COPY backend /app/backend

# Motor de visión artificial YOLO
COPY Football-Analysis-using-YOLO /app/Football-Analysis-using-YOLO

# Crear carpetas necesarias
RUN mkdir -p \
    /app/Football-Analysis-using-YOLO/input_videos \
    /app/Football-Analysis-using-YOLO/output_videos \
    /app/Football-Analysis-using-YOLO/stubs

WORKDIR /app/backend

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]