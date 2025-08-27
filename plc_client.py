from typing import Dict, Any

try:
    import snap7
except Exception:  # pragma: no cover - dependency may be missing
    snap7 = None


class PlcClient:
    """Minimal wrapper around python-snap7.

    The implementation stores PLC addresses associated with MQTT topics.  When
    running without the real `snap7` package a simple in-memory stub is used so
    that unit tests can exercise the higher level logic without requiring a
    PLC connection.
    """

    def __init__(self, config: dict, client=None):
        self._client = client
        self._items: Dict[str, str] = {}
        if self._client is None and snap7 is not None:
            self._client = snap7.client.Client()
            port = config.get("port", 102)
            self._client.connect(config.get("host"), config.get("rack", 0), config.get("slot", 2), port)

    def add_item(self, topic: str, address: str) -> None:
        self._items[topic] = address

    def write_item(self, topic: str, value: Any) -> None:
        # In the stub implementation we simply store the value so tests can
        # assert on it.  A full implementation would translate the address and
        # forward the write to the underlying snap7 client.
        if not hasattr(self, "_written"):
            self._written = {}
        self._written[topic] = value

    def read_all(self) -> Dict[str, Any]:
        # When no PLC is connected we just return zero values for all topics so
        # that the application loop can still run during tests.
        result = {}
        for topic in self._items:
            # Provide previously written values if available, otherwise 0.
            result[topic] = getattr(self, "_written", {}).get(topic, 0)
        return result