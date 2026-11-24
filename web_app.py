
import cv2
import json
import time
import threading
import joblib
import numpy as np

from collections import Counter, deque
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

from hand_tracking import HandTracker
from recognition import classify_gesture
from sign_language import SignLanguageProcessor
from voice import Voice
from storage import load_config, save_event, load_history, CONFIG_FILE


ROOT = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", 5000

MODEL_PATH = ROOT / "models" / "alphabet_model.pkl"


def open_camera(index):

    if hasattr(cv2, "CAP_AVFOUNDATION"):
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
    else:
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        cap.release()
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Algunas cámaras de macOS necesitan unos instantes para entregar el primer frame.
    for intento in range(10):
        ok, frame = cap.read()
        if ok and frame is not None:
            return cap
        time.sleep(0.3)

    cap.release()
    return None


class HandSafeEngine:

    def __init__(self):

        self.lock = threading.RLock()

        self.camera = None
        self.camera_index = None
        self.tracker = None

        self.sign_processor = SignLanguageProcessor()

        self.alphabet_model = None

        try:
            if MODEL_PATH.exists():
                self.alphabet_model = joblib.load(MODEL_PATH)

                if getattr(self.alphabet_model, "n_features_in_", 134) != 134:
                    raise ValueError(
                        "El modelo no utiliza 134 características."
                    )

                print("Modelo del alfabeto cargado correctamente.")

            else:
                print("No se encontró el modelo del alfabeto.")

        except Exception as error:
            self.alphabet_model = None
            print(f"Error cargando el modelo del alfabeto: {error}")

        self.voice = Voice(
            enabled=load_config().get("voice_enabled", True)
        )

        self.running = False
        self.thread = None
        self.latest_jpeg = None

        self.state = {
            "running": False,
            "camera_index": None,
            "gesture": "Esperando manos...",
            "category": "SIN DETECCIÓN",
            "description": "Coloca tus manos frente a la cámara",
            "confidence": 0,
            "voice_enabled": self.voice.enabled,
            "detections": 0,
            "hands_detected": 0,
            "error": "",

            "alphabet_letter": "",
            "alphabet_confidence": 0,
            "alphabet_model_loaded": self.alphabet_model is not None,
            "alphabet_status": "Módulo experimental desactivado en el reconocimiento principal"
        }

        self.recent = []
        self.alphabet_recent = deque(maxlen=5)

        self.last_announced = None
        self.last_announce_time = 0

    def scan_cameras(self):

        found = []

        for index in range(5):

            cap = open_camera(index)

            if cap is not None:

                found.append({
                    "index": index,
                    "label": f"Cámara {index}"
                })

                cap.release()

        return found

    def start(self, index):

        self.stop()

        cap = open_camera(index)

        if cap is None:

            with self.lock:
                self.state["error"] = (
                    f"No se pudo abrir la cámara {index}"
                )

            return False

        config = load_config()

        tracker = HandTracker(
            max_hands=config.get("max_hands", 2),
            detection_confidence=config.get(
                "detection_confidence", 0.65
            ),
            tracking_confidence=config.get(
                "tracking_confidence", 0.60
            )
        )

        with self.lock:

            self.camera = cap
            self.camera_index = index
            self.tracker = tracker

            self.running = True
            self.recent = []
            self.alphabet_recent.clear()

            self.last_announced = None

            self.state.update({
                "running": True,
                "camera_index": index,
                "gesture": "Esperando manos...",
                "category": "SIN DETECCIÓN",
                "description": "Coloca ambas manos frente a la cámara",
                "confidence": 0,
                "detections": 0,
                "hands_detected": 0,
                "error": "",

                "alphabet_letter": "",
                "alphabet_confidence": 0,
                "alphabet_model_loaded": self.alphabet_model is not None,
                "alphabet_status": "Módulo experimental desactivado"
            })

            self.thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )

            self.thread.start()

        return True

    def stop(self):

        with self.lock:

            self.running = False
            thread = self.thread

        if (
            thread
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=2)

        with self.lock:

            if self.camera:
                self.camera.release()

            if self.tracker:
                self.tracker.close()

            self.camera = None
            self.tracker = None
            self.thread = None
            self.latest_jpeg = None

            self.state["running"] = False
            self.state["camera_index"] = None
            self.state["hands_detected"] = 0

            self.state["alphabet_letter"] = ""
            self.state["alphabet_confidence"] = 0
            self.state["alphabet_status"] = "Cámara detenida"

    def set_voice(self, enabled):

        self.voice.enabled = bool(enabled)

        with self.lock:
            self.state["voice_enabled"] = self.voice.enabled

        config = load_config()
        config["voice_enabled"] = self.voice.enabled

        CONFIG_FILE.write_text(
            json.dumps(
                config,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    def get_state(self):

        with self.lock:
            return dict(self.state)

    def _recognize_alphabet(self, results):

        if self.alphabet_model is None:
            return None

        try:

            data = self.sign_processor.extract_features(results)

            features = data["features"]

            if features is None:
                return None

            vector = np.asarray(
                features,
                dtype=np.float64
            ).reshape(1, -1)

            probabilities = self.alphabet_model.predict_proba(vector)[0]

            best_index = int(np.argmax(probabilities))

            letter = str(
                self.alphabet_model.classes_[best_index]
            )

            confidence = float(probabilities[best_index])

            return letter, confidence

        except Exception as error:

            print(f"Error en reconocimiento del alfabeto: {error}")
            return None

    def _capture_loop(self):

        while True:

            with self.lock:

                if not self.running:
                    break

                cap = self.camera
                tracker = self.tracker

            if cap is None:
                break

            ok, frame = cap.read()

            if not ok:

                with self.lock:
                    self.state["error"] = (
                        "Se perdió la señal de la cámara."
                    )

                time.sleep(0.05)
                continue

            # Espejo para facilitar la interacción.
            frame = cv2.flip(frame, 1)

            results = tracker.process(frame)

            hands_count = 0

            if results and results.multi_hand_landmarks:

                hands = results.multi_hand_landmarks
                hands_count = len(hands)

                # Dibujar las manos detectadas.
                for i, hand_landmarks in enumerate(hands):

                    tracker.draw(frame, hand_landmarks)

                    hand_label = f"Mano {i + 1}"

                    if (
                        results.multi_handedness
                        and i < len(results.multi_handedness)
                    ):

                        hand_label = (
                            results.multi_handedness[i]
                            .classification[0].label
                        )

                    wrist = hand_landmarks.landmark[0]

                    x = int(wrist.x * frame.shape[1])
                    y = int(wrist.y * frame.shape[0])

                    cv2.putText(
                        frame,
                        hand_label,
                        (x, y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2
                    )

                # El reconocimiento del alfabeto queda desactivado en esta versión.
                # La detección de una mano no debe producir una letra automáticamente.
                with self.lock:
                    self.state["alphabet_letter"] = ""
                    self.state["alphabet_confidence"] = 0
                    self.state["alphabet_status"] = (
                        "Módulo experimental desactivado"
                    )

                # =====================================
                # RECONOCIMIENTO DE GESTOS DEL CATÁLOGO
                # =====================================

                landmarks = hands[0]
                prediction = classify_gesture(landmarks.landmark)

                if prediction:
                    label, category, description, confidence = prediction
                else:
                    label, category, description, confidence = (
                        "Gesto no reconocido",
                        "SIN DETECCIÓN",
                        "Mano detectada, esperando un gesto del catálogo",
                        0.0
                    )

                # Una mano detectada no equivale a un gesto reconocido.
                if (
                    label == "Gesto no reconocido"
                    or category == "SIN DETECCIÓN"
                    or confidence < 0.60
                ):
                    with self.lock:
                        self.recent.clear()
                        self.state.update({
                            "gesture": "Mano detectada",
                            "category": "SIN DETECCIÓN",
                            "description": (
                                "Mano detectada, esperando un gesto del catálogo"
                            ),
                            "confidence": 0,
                            "alphabet_letter": "",
                            "alphabet_confidence": 0,
                            "alphabet_status": "Módulo experimental desactivado"
                        })
                else:
                    with self.lock:
                        self.recent.append(label)
                        self.recent = self.recent[-7:]

                        stable = max(
                            set(self.recent),
                            key=self.recent.count
                        )
                        stable_count = self.recent.count(stable)

                    if stable_count >= 5 and stable == label:
                        now = time.time()

                        with self.lock:
                            self.state.update({
                                "gesture": label,
                                "category": category,
                                "description": description,
                                "confidence": confidence
                            })

                            should_announce = (
                                label != self.last_announced
                                or now - self.last_announce_time > 4
                            )

                            if should_announce:
                                self.last_announced = label
                                self.last_announce_time = now
                                self.state["detections"] += 1

                        if should_announce:
                            save_event(label, category, confidence)

                            if self.voice.enabled:
                                self.voice.speak(description)
                    else:
                        with self.lock:
                            self.state.update({
                                "gesture": "Analizando gesto...",
                                "category": "EN ANÁLISIS",
                                "description": (
                                    "Mantén la posición para confirmar el gesto"
                                ),
                                "confidence": confidence
                            })

            else:

                with self.lock:

                    self.recent.clear()
                    self.alphabet_recent.clear()

                    self.state.update({
                        "gesture": "Esperando manos...",
                        "category": "SIN DETECCIÓN",
                        "description": "Coloca tus manos frente a la cámara",
                        "confidence": 0,

                        "alphabet_letter": "",
                        "alphabet_confidence": 0,
                        "alphabet_status": "Módulo experimental desactivado"
                    })

                    if time.time() - self.last_announce_time > 1.5:
                        self.last_announced = None

            with self.lock:

                self.state["hands_detected"] = hands_count

                cv2.rectangle(
                    frame,
                    (0, 0),
                    (frame.shape[1], 54),
                    (20, 25, 35),
                    -1
                )

                cv2.putText(
                    frame,
                    "HANDSAFE AI",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (255, 255, 255),
                    2
                )

                cv2.putText(
                    frame,
                    f"Manos detectadas: {hands_count}/2",
                    (350, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )

            ok, encoded = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 82]
            )

            if ok:

                with self.lock:
                    self.latest_jpeg = encoded.tobytes()

        self.voice.close()


engine = HandSafeEngine()


class Handler(BaseHTTPRequestHandler):

    def _json(self, data, status=200):

        raw = json.dumps(
            data,
            ensure_ascii=False
        ).encode()

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(raw))
        )

        self.send_header("Cache-Control", "no-store")

        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):

        path = urlparse(self.path).path

        if path == "/":

            data = (
                ROOT / "templates" / "index.html"
            ).read_bytes()

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.end_headers()
            self.wfile.write(data)

        elif path in ("/static/styles.css", "/static/app.js"):

            file = ROOT / path.lstrip("/")

            if not file.exists():
                return self.send_error(404)

            data = file.read_bytes()

            typ = (
                "text/css"
                if path.endswith(".css")
                else "application/javascript"
            )

            self.send_response(200)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif path == "/api/cameras":

            self._json({
                "cameras": engine.scan_cameras()
            })

        elif path == "/api/state":

            self._json(engine.get_state())

        elif path == "/api/history":

            self._json({
                "history": load_history()[-20:]
            })

        elif path == "/video":

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=frame"
            )

            self.send_header(
                "Cache-Control",
                "no-cache, no-store, must-revalidate"
            )

            self.end_headers()

            try:

                while True:

                    with engine.lock:
                        frame = engine.latest_jpeg

                    if frame:

                        self.wfile.write(
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: "
                            + str(len(frame)).encode()
                            + b"\r\n\r\n"
                            + frame
                            + b"\r\n"
                        )

                    time.sleep(0.04)

            except (BrokenPipeError, ConnectionResetError):
                pass

        else:

            self.send_error(404)

    def do_POST(self):

        path = urlparse(self.path).path

        length = int(
            self.headers.get("Content-Length", 0)
        )

        try:

            payload = json.loads(
                self.rfile.read(length) or b"{}"
            )

        except json.JSONDecodeError:

            payload = {}

        if path == "/api/start":

            ok = engine.start(
                int(payload.get("index", 0))
            )

            self._json({
                "ok": ok,
                "state": engine.get_state()
            })

        elif path == "/api/stop":

            engine.stop()
            self._json({"ok": True})

        elif path == "/api/voice":

            engine.set_voice(
                payload.get("enabled", True)
            )

            self._json({
                "ok": True,
                "enabled": engine.voice.enabled
            })

        else:

            self.send_error(404)

    def log_message(self, *_):
        pass


if __name__ == "__main__":

    print(
        f"HandSafe AI: abre http://{HOST}:{PORT} en tu navegador."
    )

    print(
        "Presiona Ctrl+C en esta terminal para cerrar el servidor."
    )

    try:

        ThreadingHTTPServer(
            (HOST, PORT),
            Handler
        ).serve_forever()

    except KeyboardInterrupt:
        pass

    finally:
        engine.stop()
