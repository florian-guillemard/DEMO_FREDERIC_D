from __future__ import annotations

import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt


LOGGER = logging.getLogger(__name__)


class MqttService:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        client_id: str,
        topic_root: str,
        on_message: Callable[[str, str], None],
    ):
        self.host = host
        self.port = port
        self.topic_root = topic_root if topic_root.endswith("/") else f"{topic_root}/"
        self.on_message_cb = on_message

        self.client = mqtt.Client(client_id=client_id, transport="websockets", protocol=mqtt.MQTTv311)
        self.client.enable_logger(LOGGER)
        self.client.tls_set()
        self.client.ws_set_options(path="/mqtt")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.connected = False

    def start(self) -> None:
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect_async(self.host, self.port, keepalive=60)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def publish_json(self, topic: str, payload: dict, retain: bool = False) -> None:
        self.client.publish(topic, json.dumps(payload), qos=1, retain=retain)

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, rc: int):
        if rc == 0:
            self.connected = True
            LOGGER.info("MQTT connected to %s:%s", self.host, self.port)
            client.subscribe(f"{self.topic_root}home/+/temperature", qos=1)
            client.subscribe(f"{self.topic_root}home/+/light/state", qos=1)
            client.subscribe(f"{self.topic_root}home/+/shutter/state", qos=1)
            client.subscribe(f"{self.topic_root}home/+/fire/state", qos=1)
        else:
            LOGGER.error("MQTT connection failed, rc=%s", rc)

    def _on_disconnect(self, _client: mqtt.Client, _userdata, rc: int):
        self.connected = False
        if rc != 0:
            LOGGER.warning("Unexpected MQTT disconnection rc=%s", rc)

    def _on_message(self, _client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage):
        payload = msg.payload.decode("utf-8", errors="replace")
        self.on_message_cb(msg.topic, payload)
