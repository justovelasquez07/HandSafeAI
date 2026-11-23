import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CONFIG_FILE = DATA_DIR / "config.json"
HISTORY_FILE = DATA_DIR / "history.json"

DEFAULT_CONFIG = {
    "voice_enabled": True,
    "max_hands": 1,
    "detection_confidence": 0.65,
    "tracking_confidence": 0.60
}

def _ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False), encoding="utf-8")
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")

def load_config():
    _ensure_files()
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **data}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()

def load_history():
    _ensure_files()
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []

def save_event(gesture, category, confidence):
    history = load_history()
    history.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "gesture": gesture,
        "category": category,
        "confidence": round(float(confidence), 2)
    })
    # Limita el archivo para evitar que crezca indefinidamente.
    history = history[-500:]
    HISTORY_FILE.write_text(
        json.dumps(history, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
