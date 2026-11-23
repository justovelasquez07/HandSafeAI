
import platform
import subprocess
import threading


class Voice:
    """Salida de voz local. En macOS utiliza el comando nativo 'say'."""
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._lock = threading.Lock()
        self._process = None

    def speak(self, text):
        if not self.enabled or not text:
            return

        def run_speech():
            try:
                if platform.system() == "Darwin":
                    # Usa la voz predeterminada de macOS para evitar fallos si
                    # una voz concreta (por ejemplo, Monica) no está instalada.
                    with self._lock:
                        if self._process and self._process.poll() is None:
                            self._process.terminate()
                        self._process = subprocess.Popen(
                            ["say", text],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                else:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty("rate", 165)
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
            except Exception as exc:
                print("No se pudo reproducir la voz:", exc)
                print("Mensaje que debía pronunciarse:", text)

        threading.Thread(target=run_speech, daemon=True).start()

    def close(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
