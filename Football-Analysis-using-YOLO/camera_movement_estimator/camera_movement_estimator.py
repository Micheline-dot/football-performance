import pickle
import cv2
import numpy as np
import os
import sys

sys.path.append('../')

from utils import (
    measure_distance,
    measure_xy_distance
)


class CameraMovementEstimator:

    def __init__(self, frame):

        self.minimum_distance = 5

        self.lk_params = {
            "winSize": (15, 15),
            "maxLevel": 2,
            "criteria": (
                cv2.TERM_CRITERIA_EPS |
                cv2.TERM_CRITERIA_COUNT,
                10,
                0.03
            )
        }

        first_frame_grayscale = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        height, width = first_frame_grayscale.shape

        mask_features = np.zeros_like(
            first_frame_grayscale
        )

        # Zona izquierda
        mask_features[:, 0:min(20, width)] = 1

        # Zona derecha adaptada al tamaño real
        right_start = max(
            0,
            width - 20
        )

        mask_features[:, right_start:width] = 1

        self.features = {
            "maxCorners": 100,
            "qualityLevel": 0.3,
            "minDistance": 3,
            "blockSize": 7,
            "mask": mask_features
        }


    # ========================================================
    # AJUSTAR POSICIONES SEGÚN MOVIMIENTO DE CÁMARA
    # ========================================================

    def add_adjust_positions_to_tracks(
        self,
        tracks,
        camera_movement_per_frame
    ):

        for object_name, object_tracks in tracks.items():

            for frame_num, track in enumerate(
                object_tracks
            ):

                if frame_num >= len(
                    camera_movement_per_frame
                ):
                    break

                camera_movement = (
                    camera_movement_per_frame[
                        frame_num
                    ]
                )

                for track_id, track_info in track.items():

                    if "position" not in track_info:
                        continue

                    position = track_info[
                        "position"
                    ]

                    position_adjusted = (
                        position[0] -
                        camera_movement[0],

                        position[1] -
                        camera_movement[1]
                    )

                    tracks[
                        object_name
                    ][frame_num][track_id][
                        "position_adjusted"
                    ] = position_adjusted


    # ========================================================
    # CALCULAR MOVIMIENTO DE CÁMARA
    # ========================================================

    def get_camera_movement(
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


        if not frames:
            return []


        camera_movement = [
            [0, 0]
            for _ in range(len(frames))
        ]


        old_gray = cv2.cvtColor(
            frames[0],
            cv2.COLOR_BGR2GRAY
        )

        old_features = cv2.goodFeaturesToTrack(
            old_gray,
            **self.features
        )


        for frame_num in range(
            1,
            len(frames)
        ):

            frame_gray = cv2.cvtColor(
                frames[frame_num],
                cv2.COLOR_BGR2GRAY
            )

            camera_movement_x = 0
            camera_movement_y = 0
            max_distance = 0


            if (
                old_features is not None
                and len(old_features) > 0
            ):

                new_features, status, _ = (
                    cv2.calcOpticalFlowPyrLK(
                        old_gray,
                        frame_gray,
                        old_features,
                        None,
                        **self.lk_params
                    )
                )


                if new_features is not None:

                    if status is not None:

                        valid_old = []
                        valid_new = []

                        for i in range(
                            len(new_features)
                        ):

                            if status[i][0] == 1:

                                valid_old.append(
                                    old_features[i][0]
                                )

                                valid_new.append(
                                    new_features[i][0]
                                )


                        for new_point, old_point in zip(
                            valid_new,
                            valid_old
                        ):

                            distance = (
                                measure_distance(
                                    new_point,
                                    old_point
                                )
                            )

                            if distance > max_distance:

                                max_distance = (
                                    distance
                                )

                                (
                                    camera_movement_x,
                                    camera_movement_y
                                ) = (
                                    measure_xy_distance(
                                        old_point,
                                        new_point
                                    )
                                )


            if (
                max_distance >
                self.minimum_distance
            ):

                camera_movement[
                    frame_num
                ] = [
                    camera_movement_x,
                    camera_movement_y
                ]

                new_features = (
                    cv2.goodFeaturesToTrack(
                        frame_gray,
                        **self.features
                    )
                )

                if new_features is not None:

                    old_features = new_features


            old_gray = frame_gray


        if stub_path is not None:

            with open(
                stub_path,
                "wb"
            ) as f:

                pickle.dump(
                    camera_movement,
                    f
                )


        return camera_movement


    # ========================================================
    # DIBUJAR MOVIMIENTO DE CÁMARA
    # ========================================================

    def draw_camera_movement(
        self,
        frames,
        camera_movement_per_frame
    ):

        # IMPORTANTE:
        # No creamos output_frames.
        # Modificamos directamente cada frame.

        for frame_num, frame in enumerate(
            frames
        ):

            overlay = frame.copy()

            height, width = frame.shape[:2]

            # Caja adaptada al tamaño reducido
            box_width = min(
                150,
                width
            )

            box_height = min(
                35,
                height
            )

            cv2.rectangle(
                overlay,
                (0, 0),
                (
                    box_width,
                    box_height
                ),
                (255, 255, 255),
                -1
            )

            cv2.addWeighted(
                overlay,
                0.6,
                frame,
                0.4,
                0,
                frame
            )

            if frame_num < len(
                camera_movement_per_frame
            ):

                x_movement, y_movement = (
                    camera_movement_per_frame[
                        frame_num
                    ]
                )

            else:

                x_movement = 0
                y_movement = 0


            cv2.putText(
                frame,
                f"X:{x_movement:.1f}",
                (3, 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.32,
                (0, 0, 0),
                1
            )

            cv2.putText(
                frame,
                f"Y:{y_movement:.1f}",
                (3, 27),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.32,
                (0, 0, 0),
                1
            )


        return frames