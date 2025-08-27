from typing import Callable, Optional

try:
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover - dependency may be missing
    mqtt = None


class MqttClient:
    """Simple wrapper around paho-mqtt with a minimal API used by the connector.

    The class gracefully falls back to an in-memory stub when the real library
    is not available.  This allows the rest of the codebase to be executed in
    environments where third party packages cannot be installed (e.g. during
    tests in this kata).
    """

    def __init__(self, config: dict, message_callback: Optional[Callable[[str, str], None]] = None, client=None):
        self._config = config
        self._published = []  # type: list[tuple[str, str, bool]]
        self._subscriptions = []
        self._client = client
        if self._client is None and mqtt is not None:
            self._client = mqtt.Client()
            if message_callback is not None:
                def _on_message(client, userdata, msg):
                    message_callback(msg.topic, msg.payload.decode())
                self._client.on_message = _on_message
            if config.get("user"):
                self._client.username_pw_set(config.get("user"), config.get("password"))
            host = config.get("host", "localhost")
            self._client.connect(host)
            self._client.loop_start()

    # API compatible with mqtt_handler.js
    def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        if self._client is not None:
            self._client.publish(topic, payload, retain=retain)
        else:  # pragma: no cover - used in tests
            self._published.append((topic, payload, retain))

    def subscribe(self, topic: str) -> None:
        if self._client is not None:
            self._client.subscribe(topic)
        else:  # pragma: no cover - used in tests
            self._subscriptions.append(topic)

    def unsubscribe(self, topic: str) -> None:
        if self._client is not None:
            self._client.unsubscribe(topic)
        else:  # pragma: no cover - used in tests
            if topic in self._subscriptions:
                self._subscriptions.remove(topic)

    # Helpers for tests
    @property
    def published(self):
        return list(self._published)

    @property
    def subscriptions(self):
        return list(self._subscriptions)