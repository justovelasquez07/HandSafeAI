
"""
Clasificador geométrico inicial de HandSafe AI.

Utiliza los 21 puntos de MediaPipe para reconocer gestos estáticos.
La confianza es una estimación heurística, no una probabilidad calibrada.
"""

import math


def _distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _angle(a, b, c):
    """Calcula el ángulo ABC en grados."""
    ba = (a.x - b.x, a.y - b.y)
    bc = (c.x - b.x, c.y - b.y)

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    norm_ba = math.hypot(*ba)
    norm_bc = math.hypot(*bc)

    if norm_ba < 1e-6 or norm_bc < 1e-6:
        return 0

    cosine = dot / (norm_ba * norm_bc)
    cosine = max(-1, min(1, cosine))

    return math.degrees(math.acos(cosine))


def _finger_extended(points, mcp, pip, dip, tip):
    """
    Evalúa si un dedo está extendido mediante
    sus ángulos y distancias relativas.
    """
    angle = _angle(
        points[mcp],
        points[pip],
        points[tip]
    )

    palm = _distance(points[5], points[17])

    if palm < 1e-6:
        return False

    length = _distance(points[mcp], points[tip]) / palm

    return angle > 145 and length > 0.65


def _thumb_extended(points):
    palm = _distance(points[5], points[17])

    if palm < 1e-6:
        return False

    thumb_length = _distance(points[2], points[4]) / palm
    thumb_separation = _distance(points[4], points[5]) / palm

    return thumb_length > 0.35 and thumb_separation > 0.45


def classify_gesture(points):
    if points is None or len(points) < 21:
        return None

    index = _finger_extended(points, 5, 6, 7, 8)
    middle = _finger_extended(points, 9, 10, 11, 12)
    ring = _finger_extended(points, 13, 14, 15, 16)
    pinky = _finger_extended(points, 17, 18, 19, 20)
    thumb = _thumb_extended(points)

    fingers = [index, middle, ring, pinky]

    if all(fingers) and thumb:
        return (
            "Mano abierta",
            "NEUTRAL",
            "Se detectó una mano abierta",
            0.90
        )

    if not any(fingers) and thumb:
        return (
            "Pulgar arriba",
            "POSITIVO",
            "Pulgar arriba: gesto positivo",
            0.82
        )

    if not any(fingers) and not thumb:
        return (
            "Puño cerrado",
            "NEUTRAL",
            "Se detectó un puño cerrado",
            0.85
        )

    if index and middle and not ring and not pinky:
        return (
            "Señal de paz",
            "POSITIVO",
            "Se detectó la señal de paz",
            0.82
        )

    if middle and not index and not ring and not pinky:
        return (
            "Dedo medio levantado",
            "INAPROPIADO",
            "Alerta: se detectó un gesto que puede considerarse ofensivo",
            0.80
        )

    return (
        "Gesto no reconocido",
        "SIN DETECCIÓN",
        "Mano detectada, pero no se reconoce un gesto del catálogo",
        0.0
    )
