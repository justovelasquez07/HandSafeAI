
import cv2
import mediapipe as mp


class HandTracker:

    def __init__(
        self,
        max_hands=2,
        detection_confidence=0.65,
        tracking_confidence=0.60
    ):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            model_complexity=1,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return self.hands.process(rgb)

    def draw(self, frame, hand_landmarks):

        self.mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,

            self.mp_drawing.DrawingSpec(
                color=(80, 220, 120),
                thickness=2,
                circle_radius=3
            ),

            self.mp_drawing.DrawingSpec(
                color=(255, 180, 60),
                thickness=2
            )
        )

    def close(self):
        self.hands.close()
