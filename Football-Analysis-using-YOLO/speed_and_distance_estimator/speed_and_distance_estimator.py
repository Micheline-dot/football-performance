import cv2
from utils import measure_distance, get_foot_position


class SpeedAndDistance_Estimator:

    def __init__(self):
        self.frame_window = 12
        self.frame_rate = 24

        # Valores de control para evitar resultados imposibles
        self.max_speed_kmh = 40.0

        # Un jugador debe aparecer varias veces para considerarlo
        # un seguimiento válido.
        self.min_observations = 10

    def add_speed_and_distance_to_tracks(self, tracks):

        total_distance = {}
        valid_observations = {}

        for object_name, object_tracks in tracks.items():

            # Solo calculamos jugadores
            if object_name in ("ball", "referees"):
                continue

            number_of_frames = len(object_tracks)

            for frame_num in range(
                0,
                number_of_frames,
                self.frame_window
            ):

                last_frame = min(
                    frame_num + self.frame_window,
                    number_of_frames - 1
                )

                if last_frame <= frame_num:
                    continue

                if not object_tracks[frame_num]:
                    continue

                for track_id in list(
                    object_tracks[frame_num].keys()
                ):

                    if track_id not in object_tracks[last_frame]:
                        continue

                    start_position = (
                        object_tracks[frame_num][track_id]
                        .get("position_transformed")
                    )

                    end_position = (
                        object_tracks[last_frame][track_id]
                        .get("position_transformed")
                    )

                    if (
                        start_position is None
                        or end_position is None
                    ):
                        continue

                    time_elapsed = (
                        last_frame - frame_num
                    ) / self.frame_rate

                    if time_elapsed <= 0:
                        continue

                    # Distancia recorrida entre los dos puntos
                    distance_covered = measure_distance(
                        start_position,
                        end_position
                    )

                    if distance_covered < 0:
                        continue

                    # Velocidad
                    speed_meters_per_second = (
                        distance_covered / time_elapsed
                    )

                    speed_km_per_hour = (
                        speed_meters_per_second * 3.6
                    )

                    # ------------------------------------------------
                    # FILTRO DE VELOCIDAD
                    # ------------------------------------------------
                    #
                    # Si YOLO / la transformación genera un salto
                    # imposible, no lo utilizamos.
                    #
                    if speed_km_per_hour > self.max_speed_kmh:
                        continue

                    # Evitar valores negativos o inválidos
                    if speed_km_per_hour < 0:
                        continue

                    # Inicializar estructuras
                    if object_name not in total_distance:
                        total_distance[object_name] = {}

                    if track_id not in total_distance[object_name]:
                        total_distance[object_name][track_id] = 0.0

                    if object_name not in valid_observations:
                        valid_observations[object_name] = {}

                    if track_id not in valid_observations[object_name]:
                        valid_observations[object_name][track_id] = 0

                    # Acumular distancia SOLO si el tramo es válido
                    total_distance[object_name][track_id] += (
                        distance_covered
                    )

                    valid_observations[object_name][track_id] += 1

                    # Guardar velocidad y distancia en los frames
                    for frame_num_batch in range(
                        frame_num,
                        last_frame
                    ):

                        if (
                            track_id
                            not in object_tracks[frame_num_batch]
                        ):
                            continue

                        object_tracks[
                            frame_num_batch
                        ][track_id]["speed"] = speed_km_per_hour

                        object_tracks[
                            frame_num_batch
                        ][track_id]["distance"] = (
                            total_distance[
                                object_name
                            ][track_id]
                        )

    # ============================================================
    # MÉTRICAS PARA LA APLICACIÓN
    # ============================================================

    def get_metrics(self, tracks):

        players = {}

        velocidad_maxima = 0.0
        distancia_maxima = 0.0

        # --------------------------------------------------------
        # Determinar cantidad máxima de jugadores simultáneos
        # --------------------------------------------------------

        max_players_in_frame = 0

        for frame_tracks in tracks.get("players", []):

            cantidad = len(frame_tracks)

            if cantidad > max_players_in_frame:
                max_players_in_frame = cantidad

        # --------------------------------------------------------
        # Recopilar métricas de cada jugador
        # --------------------------------------------------------

        observaciones = {}

        for frame_tracks in tracks.get("players", []):

            for track_id, info in frame_tracks.items():

                player_key = str(track_id)

                if player_key not in players:

                    players[player_key] = {
                        "id": int(track_id),
                        "velocidad": 0.0,
                        "distancia": 0.0
                    }

                    observaciones[player_key] = 0

                speed = float(
                    info.get("speed", 0.0) or 0.0
                )

                distance = float(
                    info.get("distance", 0.0) or 0.0
                )

                # Seguridad adicional
                if speed < 0 or speed > self.max_speed_kmh:
                    continue

                if distance < 0:
                    continue

                observaciones[player_key] += 1

                # Mayor velocidad del jugador
                if speed > players[player_key]["velocidad"]:

                    players[player_key]["velocidad"] = speed

                # Mayor distancia registrada
                if distance > players[player_key]["distancia"]:

                    players[player_key]["distancia"] = distance

                # Máxima velocidad global
                if speed > velocidad_maxima:

                    velocidad_maxima = speed

                # Máxima distancia global
                if distance > distancia_maxima:

                    distancia_maxima = distance

        # --------------------------------------------------------
        # Eliminar seguimientos demasiado cortos
        # --------------------------------------------------------

        jugadores_validos = []

        for player_key, player in players.items():

            if (
                observaciones.get(player_key, 0)
                >= self.min_observations
            ):

                jugadores_validos.append(player)

        # Ordenar por velocidad
        jugadores_validos = sorted(
            jugadores_validos,
            key=lambda x: x["velocidad"],
            reverse=True
        )

        # --------------------------------------------------------
        # Si no encontramos suficientes jugadores válidos,
        # conservamos los resultados disponibles.
        # --------------------------------------------------------

        if not jugadores_validos:

            jugadores_validos = sorted(
                players.values(),
                key=lambda x: x["velocidad"],
                reverse=True
            )

        return {

            # Cantidad máxima de jugadores visibles
            "jugadores_detectados": max_players_in_frame,

            "velocidad_maxima": round(
                velocidad_maxima,
                2
            ),

            "distancia_maxima": round(
                distancia_maxima,
                2
            ),

            "jugadores": [

                {
                    "id": jugador["id"],

                    "velocidad": round(
                        jugador["velocidad"],
                        2
                    ),

                    "distancia": round(
                        jugador["distancia"],
                        2
                    )
                }

                for jugador in jugadores_validos
            ]
        }

    # ============================================================
    # DIBUJAR VELOCIDAD Y DISTANCIA EN EL VIDEO
    # ============================================================

    def draw_speed_and_distance(
        self,
        frames,
        tracks
    ):

        output_frames = []

        for frame_num, frame in enumerate(frames):

            for object_name, object_tracks in tracks.items():

                if object_name in (
                    "ball",
                    "referees"
                ):
                    continue

                if frame_num >= len(object_tracks):
                    continue

                for _, track_info in object_tracks[
                    frame_num
                ].items():

                    if "speed" not in track_info:
                        continue

                    speed = track_info.get("speed")
                    distance = track_info.get("distance")

                    if (
                        speed is None
                        or distance is None
                    ):
                        continue

                    # No mostrar velocidades imposibles
                    if speed > self.max_speed_kmh:
                        continue

                    bbox = track_info["bbox"]

                    position = list(
                        get_foot_position(bbox)
                    )

                    position[1] += 40

                    position = tuple(
                        map(int, position)
                    )

                    cv2.putText(
                        frame,
                        f"{speed:.2f} km/h",
                        position,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"{distance:.2f} m",
                        (
                            position[0],
                            position[1] + 20
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        2
                    )

            output_frames.append(frame)

        return output_frames