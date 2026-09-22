import cv2
import math


# ============================================================
# CONFIGURACIÓN DE MEMORIA
# ============================================================

# Resolución reducida para Render Free / 512 MB.
# 160 x 90 consume aproximadamente 4 veces menos RAM
# que 320 x 180.
FRAME_WIDTH = 160
FRAME_HEIGHT = 90


# ============================================================
# LEER VIDEO
# ============================================================

def read_video(video_path):

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(
            f"No se pudo abrir el video: {video_path}"
        )

    frames = []

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame = cv2.resize(
            frame,
            (FRAME_WIDTH, FRAME_HEIGHT),
            interpolation=cv2.INTER_AREA
        )

        frames.append(frame)

    cap.release()

    if not frames:
        raise RuntimeError(
            "El video no contiene frames válidos."
        )

    return frames


# ============================================================
# GUARDAR VIDEO
# ============================================================

def save_video(output_video_frames, output_video_path):

    if not output_video_frames:
        raise RuntimeError(
            "No hay frames para guardar el video."
        )

    height, width = output_video_frames[0].shape[:2]

    fourcc = cv2.VideoWriter_fourcc(
        *"XVID"
    )

    out = cv2.VideoWriter(
        output_video_path,
        fourcc,
        24,
        (width, height)
    )

    if not out.isOpened():
        raise RuntimeError(
            f"No se pudo crear el video: {output_video_path}"
        )

    try:

        for frame in output_video_frames:
            out.write(frame)

    finally:

        out.release()


# ============================================================
# GEOMETRÍA
# ============================================================

def get_center_of_bbox(bbox):

    x1, y1, x2, y2 = bbox

    return int(
        (x1 + x2) / 2
    ), int(
        (y1 + y2) / 2
    )


def get_bbox_width(bbox):

    x1, _, x2, _ = bbox

    return int(
        x2 - x1
    )


def get_foot_position(bbox):

    x1, y1, x2, y2 = bbox

    return int(
        (x1 + x2) / 2
    ), int(y2)


# ============================================================
# DISTANCIAS
# ============================================================

def measure_distance(point1, point2):

    return math.sqrt(
        (
            point1[0] -
            point2[0]
        ) ** 2
        +
        (
            point1[1] -
            point2[1]
        ) ** 2
    )


def measure_xy_distance(point1, point2):

    return (
        point1[0] - point2[0],
        point1[1] - point2[1]
    )