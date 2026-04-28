from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "domotique.db"

MQTT_HOST = os.getenv("MQTT_HOST", "broker.emqx.io")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8084"))
MQTT_TOPIC_ROOT = os.getenv("MQTT_TOPIC_ROOT", "CONNECTLEARNING/DURAND/")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "durand-domotique-dashboard")
