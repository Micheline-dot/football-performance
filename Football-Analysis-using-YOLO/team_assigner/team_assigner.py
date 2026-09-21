from sklearn.cluster import KMeans


class TeamAssigner:
    def __init__(self):
        self.team_colors = {}
        self.player_team_dict = {}

    def get_clustering_model(self, image):
        # Verificar que la imagen tenga datos
        if image is None or image.size == 0:
            return None

        # Reshape the image to 2D array
        image_2d = image.reshape(-1, 3)

        # Verificar que existan suficientes píxeles
        if len(image_2d) < 2:
            return None

        # Perform K-means with 2 clusters
        kmeans = KMeans(
            n_clusters=2,
            init="k-means++",
            n_init=1
        ).fit(image_2d)

        return kmeans

    def get_player_color(self, frame, bbox):
        height, width = frame.shape[:2]

        # Limitar el bounding box a los límites del frame
        x1 = max(0, min(int(bbox[0]), width))
        y1 = max(0, min(int(bbox[1]), height))
        x2 = max(0, min(int(bbox[2]), width))
        y2 = max(0, min(int(bbox[3]), height))

        # Verificar que el bounding box sea válido
        if x2 <= x1 or y2 <= y1:
            return None

        image = frame[y1:y2, x1:x2]

        if image.size == 0:
            return None

        top_half_image = image[0:int(image.shape[0] / 2), :]

        if top_half_image.size == 0:
            return None

        # Get Clustering model
        kmeans = self.get_clustering_model(top_half_image)

        if kmeans is None:
            return None

        # Get the cluster labels for each pixel
        labels = kmeans.labels_

        # Reshape the labels to the image shape
        clustered_image = labels.reshape(
            top_half_image.shape[0],
            top_half_image.shape[1]
        )

        # Get the player cluster
        corner_clusters = [
            clustered_image[0, 0],
            clustered_image[0, -1],
            clustered_image[-1, 0],
            clustered_image[-1, -1]
        ]

        non_player_cluster = max(
            set(corner_clusters),
            key=corner_clusters.count
        )

        player_cluster = 1 - non_player_cluster

        player_color = kmeans.cluster_centers_[player_cluster]

        return player_color

    def assign_team_color(self, frame, player_detections):

        player_colors = []

        for _, player_detection in player_detections.items():
            bbox = player_detection["bbox"]

            player_color = self.get_player_color(frame, bbox)

            # Ignorar detecciones inválidas
            if player_color is not None:
                player_colors.append(player_color)

        # Verificar que haya suficientes jugadores válidos
        if len(player_colors) < 2:
            print("No hay suficientes jugadores válidos para asignar equipos.")
            self.team_colors[1] = [255, 0, 0]
            self.team_colors[2] = [0, 0, 255]
            return

        kmeans = KMeans(
            n_clusters=2,
            init="k-means++",
            n_init=10
        ).fit(player_colors)

        self.kmeans = kmeans

        self.team_colors[1] = kmeans.cluster_centers_[0]
        self.team_colors[2] = kmeans.cluster_centers_[1]

    def get_player_team(self, frame, player_bbox, player_id):

        if player_id in self.player_team_dict:
            return self.player_team_dict[player_id]

        player_color = self.get_player_color(
            frame,
            player_bbox
        )

        # Si no se pudo obtener el color, asignar equipo 1
        if player_color is None:
            team_id = 1
        else:
            team_id = self.kmeans.predict(
                player_color.reshape(1, -1)
            )[0]

            team_id += 1

        if player_id == 91:
            team_id = 1

        self.player_team_dict[player_id] = team_id

        return team_id
