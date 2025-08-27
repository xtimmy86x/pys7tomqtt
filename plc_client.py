import logging
import re
import struct
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
        """Read all configured items from the PLC.

        Each stored address is expected to use the S7 DB notation, e.g.::

            DB1.DBX0.0   # bool
            DB1.DBW2     # 16-bit int
            DB1.DBD4     # 32-bit float

        When the snap7 client is not available the method falls back to the
        in-memory values written via :meth:`write_item` so that tests can run
        without a real PLC connection.
        """

        result: Dict[str, Any] = {}
        for topic, address in self._items.items():
            if self._client is None:
                # Provide previously written values if available, otherwise 0.
                result[topic] = getattr(self, "_written", {}).get(topic, 0)
                continue

            try:
                db, dtype, byte, bit = self._parse_address(address)
                size = {"X": 1, "B": 1, "W": 2, "D": 4}[dtype]
                area = snap7.type.Areas.DB if snap7 is not None else 0
                raw = self._client.read_area(area, db, byte, size)

                if dtype == "X":
                    result[topic] = bool(raw[0] & (1 << bit))
                elif dtype == "D":
                    # Treat double word as float for simplicity
                    result[topic] = struct.unpack(">f", raw)[0]
                elif dtype == "W":
                    result[topic] = int.from_bytes(raw, byteorder="big", signed=True)
                else:  # "B"
                    result[topic] = raw[0]
            except Exception:  # pragma: no cover - connection/parsing errors
                logging.exception("Failed to read address %s", address)
        return result

    @staticmethod
    def _parse_address(address: str) -> tuple[int, str, int, int]:
        """Parse an S7 DB address.

        Returns a tuple of ``(db_number, data_type, byte_offset, bit_offset)``.
        ``bit_offset`` is zero when not used.
        """

        match = re.fullmatch(r"DB(\d+)\.(?:DB)?([XBWD])(\d+)(?:\.(\d+))?", address.upper())
        if not match:
            raise ValueError(f"Unsupported address format: {address}")
        db = int(match.group(1))
        dtype = match.group(2)
        byte = int(match.group(3))
        bit = int(match.group(4) or 0)
        return db, dtype, byte, bit
