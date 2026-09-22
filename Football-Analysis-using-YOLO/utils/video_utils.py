import cv2


def read_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # Reducir resolución para disminuir el uso de memoria en Render
        frame = cv2.resize(frame, (640, 360))

        frames.append(frame)

    cap.release()

    return frames


def save_video(output_video_frames, output_video_path):
    if not output_video_frames:
        raise RuntimeError("No hay frames para guardar el video.")

    fourcc = cv2.VideoWriter_fourcc(*"XVID")

    out = cv2.VideoWriter(
        output_video_path,
        fourcc,
        24,
        (
            output_video_frames[0].shape[1],
            output_video_frames[0].shape[0]
        )
    )

    for frame in output_video_frames:
        out.write(frame)

    out.release()