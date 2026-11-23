
import math


class SignLanguageProcessor:
    """
    Procesa los puntos de referencia de ambas manos
    para preparar características destinadas al
    reconocimiento de Lengua de Señas Nicaragüense.
    """

    LANDMARKS_PER_HAND = 21
    COORDINATES_PER_POINT = 3

    def __init__(self):
        self.last_features = None

    def _distance(self, point_a, point_b):
        """
        Calcula la distancia entre dos puntos 3D.
        """

        return math.sqrt(
            (point_a.x - point_b.x) ** 2
            + (point_a.y - point_b.y) ** 2
            + (point_a.z - point_b.z) ** 2
        )

    def _extract_hand_features(self, hand_landmarks):
        """
        Extrae características de una mano.

        Conserva:
        - Posición de la muñeca.
        - Posición relativa de los 21 puntos.
        - Proporciones de la mano.
        """

        landmarks = hand_landmarks.landmark

        wrist = landmarks[0]
        middle_mcp = landmarks[9]

        # Escala de referencia de la palma
        scale = self._distance(wrist, middle_mcp)

        if scale < 0.000001:
            scale = 0.000001

        features = []

        # Posición de la muñeca en la imagen.
        # Esto ayuda a conservar la ubicación de cada mano.
        features.extend([
            float(wrist.x),
            float(wrist.y),
            float(wrist.z)
        ])

        # Posiciones relativas de los 21 puntos.
        for point in landmarks:

            relative_x = (point.x - wrist.x) / scale
            relative_y = (point.y - wrist.y) / scale
            relative_z = (point.z - wrist.z) / scale

            features.extend([
                float(relative_x),
                float(relative_y),
                float(relative_z)
            ])

        return features

    def extract_features(self, results):
        """
        Extrae las características de ambas manos.

        Orden:
        1. Mano izquierda.
        2. Mano derecha.

        Si falta una mano, reserva un vector de ceros
        para mantener una longitud fija.
        """

        left_hand = None
        right_hand = None

        hand_labels = []

        if (
            results is None
            or not results.multi_hand_landmarks
        ):
            self.last_features = None

            return {
                "features": None,
                "hands_detected": 0,
                "hand_labels": []
            }

        landmarks_list = results.multi_hand_landmarks
        handedness_list = results.multi_handedness or []

        for index, hand_landmarks in enumerate(landmarks_list):

            label = "Unknown"

            if index < len(handedness_list):

                classification = (
                    handedness_list[index].classification
                )

                if classification:
                    label = classification[0].label

            hand_labels.append(label)

            if label == "Left" and left_hand is None:
                left_hand = hand_landmarks

            elif label == "Right" and right_hand is None:
                right_hand = hand_landmarks

            else:
                # Respaldo si MediaPipe no identifica
                # correctamente una de las manos.
                if left_hand is None:
                    left_hand = hand_landmarks
                elif right_hand is None:
                    right_hand = hand_landmarks

        # Cada mano tiene 66 características:
        # 3 de muñeca + 21 puntos * 3 coordenadas.
        hand_feature_size = (
            3 + self.LANDMARKS_PER_HAND
            * self.COORDINATES_PER_POINT
        )

        empty_hand = [0.0] * hand_feature_size

        left_features = (
            self._extract_hand_features(left_hand)
            if left_hand is not None
            else empty_hand.copy()
        )

        right_features = (
            self._extract_hand_features(right_hand)
            if right_hand is not None
            else empty_hand.copy()
        )

        # Vector final de longitud fija:
        # 66 izquierda + 66 derecha + 2 indicadores.
        features = (
            left_features
            + right_features
            + [
                1.0 if left_hand is not None else 0.0,
                1.0 if right_hand is not None else 0.0
            ]
        )

        self.last_features = features

        return {
            "features": features,
            "hands_detected": len(landmarks_list),
            "hand_labels": hand_labels
        }

    def reset(self):
        """
        Limpia las características anteriores.
        """

        self.last_features = None
