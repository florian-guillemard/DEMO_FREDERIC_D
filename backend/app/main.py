from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import DB_PATH, FRONTEND_DIR, MQTT_CLIENT_ID, MQTT_HOST, MQTT_PORT, MQTT_TOPIC_ROOT
from .models import RoomsStateResponse, ToggleResponse
from .mqtt_client import MqttService
from .storage import TemperatureStore
from .topics import ROOMS, parse_topic, topic_for


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

app = FastAPI(title="Domotique Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = TemperatureStore(DB_PATH)

room_states = {
    room: {
        "light_on": False,
        "shutter_open": False,
        "temperature": None,
        "fire_state": "NORMAL",
        "updated_at": datetime.utcnow().isoformat(),
    }
    for room in ROOMS
}


class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event_type: str, payload: dict):
        message = {"type": event_type, "payload": payload}
        alive: list[WebSocket] = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
                alive.append(ws)
            except Exception:  # noqa: BLE001
                pass
        self.connections = alive


ws_manager = ConnectionManager()
MAIN_LOOP: asyncio.AbstractEventLoop | None = None


async def broadcast_room_state(room: str) -> None:
    await ws_manager.broadcast("room_state", {"room": room, "state": room_states[room]})


async def handle_mqtt_event(topic: str, payload: str):
    parsed = parse_topic(MQTT_TOPIC_ROOT, topic)
    if not parsed:
        return

    room = parsed["room"]
    device = parsed["device"]
    kind = parsed["kind"]
    now = datetime.utcnow().isoformat()

    if device == "temperature":
        try:
            data = json.loads(payload)
            value = float(data["value"])
        except (ValueError, KeyError, json.JSONDecodeError):
            LOGGER.warning("Invalid temperature payload on %s: %s", topic, payload)
            return

        room_states[room]["temperature"] = value
        room_states[room]["updated_at"] = now
        store.insert_temperature(room, value)
        await ws_manager.broadcast("temperature", {"room": room, "value": value, "updated_at": now})
        return

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        LOGGER.warning("Invalid JSON payload on %s: %s", topic, payload)
        return

    if device == "light" and kind == "state":
        room_states[room]["light_on"] = bool(data.get("on", False))
    elif device == "shutter" and kind == "state":
        room_states[room]["shutter_open"] = str(data.get("state", "CLOSE")).upper() == "OPEN"
    elif device == "fire" and kind == "state":
        fire_state = str(data.get("state", "NORMAL")).upper()
        room_states[room]["fire_state"] = "ALERT" if fire_state == "ALERT" else "NORMAL"

    room_states[room]["updated_at"] = now
    await broadcast_room_state(room)


def mqtt_message_handler(topic: str, payload: str):
    if MAIN_LOOP is None:
        LOGGER.warning("Main event loop is unavailable, skipping MQTT message")
        return
    asyncio.run_coroutine_threadsafe(handle_mqtt_event(topic, payload), MAIN_LOOP)


mqtt_service = MqttService(
    host=MQTT_HOST,
    port=MQTT_PORT,
    client_id=MQTT_CLIENT_ID,
    topic_root=MQTT_TOPIC_ROOT,
    on_message=mqtt_message_handler,
)


@app.on_event("startup")
async def on_startup():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    mqtt_service.start()


@app.on_event("shutdown")
async def on_shutdown():
    mqtt_service.stop()


@app.get("/api/rooms/state", response_model=RoomsStateResponse)
async def get_rooms_state():
    return {"rooms": room_states}


@app.post("/api/rooms/{room}/light/toggle", response_model=ToggleResponse)
async def toggle_light(room: str):
    if room not in room_states:
        raise HTTPException(status_code=404, detail="Room not found")
    next_state = not bool(room_states[room]["light_on"])
    room_states[room]["light_on"] = next_state
    room_states[room]["updated_at"] = datetime.utcnow().isoformat()
    await broadcast_room_state(room)
    mqtt_service.publish_json(
        topic_for(MQTT_TOPIC_ROOT, room, "light", "set"),
        {"on": next_state, "source": "ui", "ts": datetime.utcnow().isoformat()},
    )
    return {"room": room, "ok": True, "command": "light.toggle"}


@app.post("/api/rooms/{room}/shutter/toggle", response_model=ToggleResponse)
async def toggle_shutter(room: str):
    if room not in room_states:
        raise HTTPException(status_code=404, detail="Room not found")
    next_open = not bool(room_states[room]["shutter_open"])
    command = "OPEN" if next_open else "CLOSE"
    room_states[room]["shutter_open"] = next_open
    room_states[room]["updated_at"] = datetime.utcnow().isoformat()
    await broadcast_room_state(room)
    mqtt_service.publish_json(
        topic_for(MQTT_TOPIC_ROOT, room, "shutter", "set"),
        {"command": command, "source": "ui", "ts": datetime.utcnow().isoformat()},
    )
    return {"room": room, "ok": True, "command": "shutter.toggle"}


@app.post("/api/rooms/{room}/fire/test", response_model=ToggleResponse)
async def test_fire_detector(room: str):
    if room not in room_states:
        raise HTTPException(status_code=404, detail="Room not found")
    mqtt_service.publish_json(
        topic_for(MQTT_TOPIC_ROOT, room, "fire", "test"),
        {"test": True, "source": "ui", "ts": datetime.utcnow().isoformat()},
    )
    return {"room": room, "ok": True, "command": "fire.test"}


@app.get("/api/rooms/{room}/temperature/history")
async def room_temperature_history(
    room: str,
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None),
    bucket: str = Query(default="hour"),
):
    if room not in room_states:
        raise HTTPException(status_code=404, detail="Room not found")

    del bucket  # Reserved for later aggregation strategies.
    end = to_ts or datetime.utcnow()
    start = from_ts or (end - timedelta(hours=24))
    points = store.get_history(room, start, end)
    return {"room": room, "points": points}


@app.websocket("/ws/state")
async def state_socket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    await websocket.send_json({"type": "snapshot", "payload": {"rooms": room_states}})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
