from ultralytics import YOLO
import supervision as sv
import pickle
import os
import numpy as np
import pandas as pd
import cv2
import sys

sys.path.append('../')

from utils import (
    get_center_of_bbox,
    get_bbox_width,
    get_foot_position
)


class Tracker:

    def __init__(self, model_path):

        self.model = YOLO(model_path)

        self.tracker = sv.ByteTrack()


    # ========================================================
    # POSICIONES
    # ========================================================

    def add_position_to_tracks(self, tracks):

        for object_name, object_tracks in tracks.items():

            for frame_num, track in enumerate(
                object_tracks
            ):

                for track_id, track_info in track.items():

                    bbox = track_info["bbox"]

                    if object_name == "ball":

                        position = (
                            get_center_of_bbox(
                                bbox
                            )
                        )

                    else:

                        position = (
                            get_foot_position(
                                bbox
                            )
                        )

                    tracks[
                        object_name
                    ][frame_num][track_id][
                        "position"
                    ] = position


    # ========================================================
    # INTERPOLAR BALÓN
    # ========================================================

    def interpolate_ball_positions(
        self,
        ball_positions
    ):

        rows = []

        for frame_tracks in ball_positions:

            bbox = (
                frame_tracks
                .get(1, {})
                .get("bbox")
            )

            if (
                bbox is None
                or len(bbox) != 4
            ):

                bbox = [
                    np.nan,
                    np.nan,
                    np.nan,
                    np.nan
                ]

            rows.append(bbox)


        if not rows:
            return []


        df_ball_positions = pd.DataFrame(
            rows,
            columns=[
                "x1",
                "y1",
                "x2",
                "y2"
            ]
        )


        df_ball_positions = (
            df_ball_positions.replace(
                [np.inf, -np.inf],
                np.nan
            )
        )


        df_ball_positions = (
            df_ball_positions.interpolate(
                limit_direction="both"
            )
        )


        df_ball_positions = (
            df_ball_positions.bfill().ffill()
        )


        if df_ball_positions.isna().all().all():

            df_ball_positions = pd.DataFrame(
                np.zeros(
                    (
                        len(rows),
                        4
                    )
                ),
                columns=[
                    "x1",
                    "y1",
                    "x2",
                    "y2"
                ]
            )

        else:

            df_ball_positions = (
                df_ball_positions.fillna(0)
            )


        ball_positions = []

        for _, row in (
            df_ball_positions.iterrows()
        ):

            ball_positions.append(
                {
                    1: {
                        "bbox": row.tolist()
                    }
                }
            )


        return ball_positions


    # ========================================================
    # DETECCIÓN
    # ========================================================

    def detect_frames(self, frames):

        for frame in frames:

            detections = self.model.predict(
                frame,
                conf=0.1,
                verbose=False
            )

            if detections:

                yield detections[0]


    # ========================================================
    # TRACKING
    # ========================================================

    def get_object_tracks(
        self,
        frames,
        read_from_stub=False,
        stub_path=None
    ):

        if (
            read_from_stub
            and stub_path is not None
            and os.path.exists(stub_path)
        ):

            with open(
                stub_path,
                "rb"
            ) as f:

                return pickle.load(f)


        tracks = {
            "players": [],
            "referees": [],
            "ball": []
        }


        for frame_num, detection in enumerate(
            self.detect_frames(frames)
        ):

            cls_names = detection.names

            cls_names_inv = {
                value: key
                for key, value in cls_names.items()
            }


            detection_supervision = (
                sv.Detections.from_ultralytics(
                    detection
                )
            )


            # ------------------------------------------------
            # CONVERTIR GOALKEEPER EN PLAYER
            # ------------------------------------------------

            for object_ind, class_id in enumerate(
                detection_supervision.class_id
            ):

                if (
                    class_id in cls_names
                    and cls_names[class_id]
                    == "goalkeeper"
                ):

                    if "player" in cls_names_inv:

                        detection_supervision.class_id[
                            object_ind
                        ] = cls_names_inv[
                            "player"
                        ]


            # ------------------------------------------------
            # BYTE TRACK
            # ------------------------------------------------

            detection_with_tracks = (
                self.tracker.update_with_detections(
                    detection_supervision
                )
            )


            tracks["players"].append({})
            tracks["referees"].append({})
            tracks["ball"].append({})


            # ------------------------------------------------
            # JUGADORES Y ÁRBITROS
            # ------------------------------------------------

            for frame_detection in (
                detection_with_tracks
            ):

                bbox = (
                    frame_detection[0]
                    .tolist()
                )

                cls_id = frame_detection[3]

                track_id = frame_detection[4]


                if (
                    "player" in cls_names_inv
                    and cls_id ==
                    cls_names_inv["player"]
                ):

                    tracks[
                        "players"
                    ][frame_num][track_id] = {
                        "bbox": bbox
                    }


                if (
                    "referee" in cls_names_inv
                    and cls_id ==
                    cls_names_inv["referee"]
                ):

                    tracks[
                        "referees"
                    ][frame_num][track_id] = {
                        "bbox": bbox
                    }


            # ------------------------------------------------
            # BALÓN
            # ------------------------------------------------

            for frame_detection in (
                detection_supervision
            ):

                bbox = (
                    frame_detection[0]
                    .tolist()
                )

                cls_id = frame_detection[3]


                if (
                    "ball" in cls_names_inv
                    and cls_id ==
                    cls_names_inv["ball"]
                ):

                    tracks[
                        "ball"
                    ][frame_num][1] = {
                        "bbox": bbox
                    }


        # ----------------------------------------------------
        # GUARDAR STUB
        # ----------------------------------------------------

        if stub_path is not None:

            with open(
                stub_path,
                "wb"
            ) as f:

                pickle.dump(
                    tracks,
                    f
                )


        return tracks


    # ========================================================
    # DIBUJAR ELIPSE
    # ========================================================

    def draw_ellipse(
        self,
        frame,
        bbox,
        color,
        track_id=None
    ):

        y2 = int(bbox[3])

        x_center, _ = (
            get_center_of_bbox(
                bbox
            )
        )

        width = get_bbox_width(
            bbox
        )


        cv2.ellipse(
            frame,
            center=(
                x_center,
                y2
            ),
            axes=(
                int(width),
                int(
                    0.35 * width
                )
            ),
            angle=0.0,
            startAngle=-45,
            endAngle=235,
            color=color,
            thickness=2,
            lineType=cv2.LINE_4
        )


        rectangle_width = 20
        rectangle_height = 10


        x1_rect = (
            x_center -
            rectangle_width // 2
        )

        x2_rect = (
            x_center +
            rectangle_width // 2
        )

        y1_rect = (
            y2 -
            rectangle_height // 2
        )

        y2_rect = (
            y2 +
            rectangle_height // 2
        )


        if track_id is not None:

            cv2.rectangle(
                frame,
                (
                    int(x1_rect),
                    int(y1_rect)
                ),
                (
                    int(x2_rect),
                    int(y2_rect)
                ),
                color,
                cv2.FILLED
            )


            cv2.putText(
                frame,
                f"{track_id}",
                (
                    int(
                        x1_rect + 3
                    ),
                    int(
                        y1_rect + 8
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.3,
                (0, 0, 0),
                1
            )


        return frame


    # ========================================================
    # TRIÁNGULO
    # ========================================================

    def draw_traingle(
        self,
        frame,
        bbox,
        color
    ):

        y = int(bbox[1])

        x, _ = (
            get_center_of_bbox(
                bbox
            )
        )


        triangle_points = np.array(
            [
                [x, y],
                [x - 5, y - 10],
                [x + 5, y - 10]
            ]
        )


        cv2.drawContours(
            frame,
            [triangle_points],
            0,
            color,
            cv2.FILLED
        )


        cv2.drawContours(
            frame,
            [triangle_points],
            0,
            (0, 0, 0),
            1
        )


        return frame


    # ========================================================
    # CONTROL DEL BALÓN
    # ========================================================

    def draw_team_ball_control(
        self,
        frame,
        frame_num,
        team_ball_control,
        team1_count,
        team2_count
    ):

        h, w = frame.shape[:2]


        x1 = max(
            0,
            w - 155
        )

        y1 = max(
            0,
            h - 25
        )

        x2 = w - 2
        y2 = h - 2


        overlay = frame.copy()


        cv2.rectangle(
            overlay,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            -1
        )


        cv2.addWeighted(
            overlay,
            0.4,
            frame,
            0.6,
            0,
            frame
        )


        total = (
            team1_count +
            team2_count
        )


        if total > 0:

            team_1 = (
                team1_count /
                total
            )

            team_2 = (
                team2_count /
                total
            )

        else:

            team_1 = 0
            team_2 = 0


        cv2.putText(
            frame,
            f"T1: {team_1 * 100:.0f}%",
            (
                x1 + 5,
                y1 + 10
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.28,
            (0, 0, 0),
            1
        )


        cv2.putText(
            frame,
            f"T2: {team_2 * 100:.0f}%",
            (
                x1 + 5,
                y1 + 21
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.28,
            (0, 0, 0),
            1
        )


        return frame


    # ========================================================
    # DIBUJAR ANOTACIONES
    # ========================================================

    def draw_annotations(
        self,
        video_frames,
        tracks,
        team_ball_control
    ):

        team1_count = 0
        team2_count = 0


        for frame_num, frame in enumerate(
            video_frames
        ):

            player_dict = (
                tracks[
                    "players"
                ][frame_num]
            )

            ball_dict = (
                tracks[
                    "ball"
                ][frame_num]
            )

            referee_dict = (
                tracks[
                    "referees"
                ][frame_num]
            )


            # ------------------------------------------------
            # POSESIÓN
            # ------------------------------------------------

            if frame_num < len(
                team_ball_control
            ):

                if (
                    team_ball_control[
                        frame_num
                    ] == 1
                ):

                    team1_count += 1

                elif (
                    team_ball_control[
                        frame_num
                    ] == 2
                ):

                    team2_count += 1


            # ------------------------------------------------
            # JUGADORES
            # ------------------------------------------------

            for track_id, player in (
                player_dict.items()
            ):

                color = player.get(
                    "team_color",
                    (0, 0, 255)
                )


                self.draw_ellipse(
                    frame,
                    player["bbox"],
                    color,
                    track_id
                )


                if player.get(
                    "has_ball",
                    False
                ):

                    self.draw_traingle(
                        frame,
                        player["bbox"],
                        (0, 0, 255)
                    )


            # ------------------------------------------------
            # ÁRBITROS
            # ------------------------------------------------

            for _, referee in (
                referee_dict.items()
            ):

                self.draw_ellipse(
                    frame,
                    referee["bbox"],
                    (0, 255, 255)
                )


            # ------------------------------------------------
            # BALÓN
            # ------------------------------------------------

            for _, ball in (
                ball_dict.items()
            ):

                self.draw_traingle(
                    frame,
                    ball["bbox"],
                    (0, 255, 0)
                )


            # ------------------------------------------------
            # CONTROL DEL BALÓN
            # ------------------------------------------------

            self.draw_team_ball_control(
                frame,
                frame_num,
                team_ball_control,
                team1_count,
                team2_count
            )


        return video_frames