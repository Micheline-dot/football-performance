from utils import (
    read_video,
    save_video
)

from trackers import Tracker

from camera_movement_estimator import (
    CameraMovementEstimator
)

from view_transformer import ViewTransformer

from speed_and_distance_estimator import (
    SpeedAndDistance_Estimator
)

from team_assigner import TeamAssigner

from player_ball_assigner import (
    PlayerBallAssigner
)

import numpy as np
import json
import os
import gc


# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_VIDEO = "./input_videos/match.mp4"

OUTPUT_VIDEO = (
    "./output_videos/output_video.avi"
)

METRICS_FILE = (
    "./output_videos/metrics.json"
)

TRACK_STUB = (
    "stubs/track_stubs.pkl"
)

CAMERA_STUB = (
    "stubs/camera_movement_stub.pkl"
)


# ============================================================
# MAIN
# ============================================================

def main():

    print("======================================")
    print("INICIANDO ANÁLISIS")
    print("======================================")


    # --------------------------------------------------------
    # LEER VIDEO
    # --------------------------------------------------------

    print("Leyendo video...")

    video_frames = read_video(
        INPUT_VIDEO
    )

    print(
        f"Frames cargados: "
        f"{len(video_frames)}"
    )


    if not video_frames:

        raise RuntimeError(
            "No se pudieron leer frames del video."
        )


    # --------------------------------------------------------
    # TRACKER
    # --------------------------------------------------------

    print("Cargando modelo YOLO...")

    tracker = Tracker(
        "./models/best.pt"
    )


    print("Detectando jugadores, árbitros y balón...")


    tracks = tracker.get_object_tracks(
        video_frames,
        read_from_stub=False,
        stub_path=TRACK_STUB
    )


    print("Tracking terminado.")


    # --------------------------------------------------------
    # POSICIONES
    # --------------------------------------------------------

    tracker.add_position_to_tracks(
        tracks
    )


    # --------------------------------------------------------
    # MOVIMIENTO DE CÁMARA
    # --------------------------------------------------------

    print(
        "Calculando movimiento de cámara..."
    )


    camera_movement_estimator = (
        CameraMovementEstimator(
            video_frames[0]
        )
    )


    camera_movement_per_frame = (
        camera_movement_estimator
        .get_camera_movement(
            video_frames,
            read_from_stub=False,
            stub_path=CAMERA_STUB
        )
    )


    camera_movement_estimator.add_adjust_positions_to_tracks(
        tracks,
        camera_movement_per_frame
    )


    # --------------------------------------------------------
    # TRANSFORMACIÓN
    # --------------------------------------------------------

    view_transformer = ViewTransformer()

    view_transformer.add_transformed_position_to_tracks(
        tracks
    )


    # --------------------------------------------------------
    # INTERPOLAR BALÓN
    # --------------------------------------------------------

    print(
        "Interpolando posiciones del balón..."
    )

    tracks["ball"] = (
        tracker.interpolate_ball_positions(
            tracks["ball"]
        )
    )


    # --------------------------------------------------------
    # VELOCIDAD Y DISTANCIA
    # --------------------------------------------------------

    speed_and_distance_estimator = (
        SpeedAndDistance_Estimator()
    )


    speed_and_distance_estimator.add_speed_and_distance_to_tracks(
        tracks
    )


    # --------------------------------------------------------
    # ASIGNACIÓN DE EQUIPOS
    # --------------------------------------------------------

    print(
        "Asignando equipos..."
    )


    team_assigner = TeamAssigner()


    team_assigner.assign_team_color(
        video_frames[0],
        tracks["players"][0]
    )


    for frame_num, player_track in enumerate(
        tracks["players"]
    ):

        for player_id, track in (
            player_track.items()
        ):

            team = (
                team_assigner
                .get_player_team(
                    video_frames[
                        frame_num
                    ],
                    track["bbox"],
                    player_id
                )
            )


            tracks[
                "players"
            ][frame_num][player_id][
                "team"
            ] = team


            tracks[
                "players"
            ][frame_num][player_id][
                "team_color"
            ] = (
                team_assigner
                .team_colors[team]
            )


    # --------------------------------------------------------
    # CONTROL DEL BALÓN
    # --------------------------------------------------------

    print(
        "Calculando posesión del balón..."
    )


    player_assigner = (
        PlayerBallAssigner()
    )


    team_ball_control = []

    last_team = 1


    for frame_num, player_track in enumerate(
        tracks["players"]
    ):

        ball_data = (
            tracks[
                "ball"
            ][frame_num]
            .get(1)
        )


        if ball_data is None:

            team_ball_control.append(
                last_team
            )

            continue


        ball_bbox = (
            ball_data["bbox"]
        )


        assigned_player = (
            player_assigner
            .assign_ball_to_player(
                player_track,
                ball_bbox
            )
        )


        if assigned_player != -1:

            assigned_team = (
                tracks[
                    "players"
                ][frame_num][
                    assigned_player
                ].get(
                    "team",
                    last_team
                )
            )

            last_team = assigned_team


        team_ball_control.append(
            last_team
        )


    team_ball_control = np.array(
        team_ball_control,
        dtype=int
    )


    # --------------------------------------------------------
    # MÉTRICAS
    # --------------------------------------------------------

    print(
        "Generando métricas..."
    )


    metricas = (
        speed_and_distance_estimator
        .get_metrics(
            tracks
        )
    )


    os.makedirs(
        "./output_videos",
        exist_ok=True
    )


    with open(
        METRICS_FILE,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            metricas,
            archivo,
            ensure_ascii=False,
            indent=2
        )


    # --------------------------------------------------------
    # ANOTACIONES
    # --------------------------------------------------------

    print(
        "Dibujando detecciones..."
    )


    output_video_frames = (
        tracker.draw_annotations(
            video_frames,
            tracks,
            team_ball_control
        )
    )


    # --------------------------------------------------------
    # MOVIMIENTO DE CÁMARA
    # --------------------------------------------------------

    output_video_frames = (
        camera_movement_estimator
        .draw_camera_movement(
            output_video_frames,
            camera_movement_per_frame
        )
    )


    # --------------------------------------------------------
    # VELOCIDAD Y DISTANCIA EN VIDEO
    # --------------------------------------------------------

    speed_and_distance_estimator.draw_speed_and_distance(
        output_video_frames,
        tracks
    )


    # --------------------------------------------------------
    # GUARDAR VIDEO
    # --------------------------------------------------------

    print(
        "Guardando video..."
    )


    save_video(
        output_video_frames,
        OUTPUT_VIDEO
    )


    # --------------------------------------------------------
    # LIMPIAR REFERENCIAS
    # --------------------------------------------------------

    del output_video_frames
    del camera_movement_per_frame

    gc.collect()


    print("======================================")
    print("ANÁLISIS COMPLETADO")
    print("======================================")


if __name__ == "__main__":

    main()