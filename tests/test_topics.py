from backend.app.topics import parse_topic, topic_for


ROOT = "CONNECTLEARNING/DURAND/"


def test_topic_for_temperature():
    assert topic_for(ROOT, "salon", "temperature") == "CONNECTLEARNING/DURAND/home/salon/temperature"


def test_topic_for_light_state():
    assert topic_for(ROOT, "cuisine", "light", "state") == "CONNECTLEARNING/DURAND/home/cuisine/light/state"


def test_parse_temperature_topic():
    data = parse_topic(ROOT, "CONNECTLEARNING/DURAND/home/chambre1/temperature")
    assert data == {"room": "chambre1", "device": "temperature", "kind": "telemetry"}


def test_parse_device_state_topic():
    data = parse_topic(ROOT, "CONNECTLEARNING/DURAND/home/wc/fire/state")
    assert data == {"room": "wc", "device": "fire", "kind": "state"}


def test_parse_invalid_room_topic():
    data = parse_topic(ROOT, "CONNECTLEARNING/DURAND/home/garage/fire/state")
    assert data is None
