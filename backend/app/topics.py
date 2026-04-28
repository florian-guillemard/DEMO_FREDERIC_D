from typing import Literal


ROOMS = [
    "salle_de_bain",
    "wc",
    "chambre1",
    "chambre2",
    "salon",
    "cuisine",
]

TopicDevice = Literal["temperature", "light", "shutter", "fire"]
TopicKind = Literal["set", "state", "test"]


def normalize_root(topic_root: str) -> str:
    return topic_root if topic_root.endswith("/") else f"{topic_root}/"


def topic_for(topic_root: str, room: str, device: TopicDevice, kind: TopicKind | None = None) -> str:
    root = normalize_root(topic_root)
    if device == "temperature":
        return f"{root}home/{room}/temperature"
    if kind is None:
        raise ValueError("kind is required for non-temperature devices")
    return f"{root}home/{room}/{device}/{kind}"


def parse_topic(topic_root: str, full_topic: str) -> dict[str, str] | None:
    root = normalize_root(topic_root)
    if not full_topic.startswith(root):
        return None

    suffix = full_topic[len(root) :]
    parts = suffix.split("/")
    if len(parts) == 3 and parts[0] == "home" and parts[2] == "temperature":
        room = parts[1]
        if room not in ROOMS:
            return None
        return {"room": room, "device": "temperature", "kind": "telemetry"}

    if len(parts) == 4 and parts[0] == "home":
        room, device, kind = parts[1], parts[2], parts[3]
        if room not in ROOMS:
            return None
        if device not in {"light", "shutter", "fire"}:
            return None
        if kind not in {"set", "state", "test"}:
            return None
        return {"room": room, "device": device, "kind": kind}
    return None
