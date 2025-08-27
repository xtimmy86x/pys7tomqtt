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
        """Write a single item to the PLC.

        The method always stores the value in an in-memory dictionary so that
        :meth:`read_all` can fall back to it when the real ``snap7`` package is
        unavailable (e.g. during tests).  When a snap7 client is present the
        address for the given topic is translated and forwarded to
        ``write_area``.
        """

        if not hasattr(self, "_written"):
            self._written = {}
        self._written[topic] = value

        if self._client is None:
            return

        address = self._items.get(topic)
        if address is None:  # pragma: no cover - misconfiguration
            return

        try:
            db, dtype, byte, bit = self._parse_address(address)
            dt = dtype  # already upper() in _parse_address

            area = snap7.type.Areas.DB if snap7 is not None else 0

            if dt == "X":
                # Leggi il byte esistente per preservare gli altri bit
                existing_byte = 0
                try:
                    current = self._client.read_area(area, db, byte, 1)
                    if current and len(current) >= 1:
                        existing_byte = current[0]
                except Exception:
                    logging.debug("Impossibile leggere il byte esistente per %s, procedo con 0.", address)
                if not (0 <= bit <= 7):
                    raise ValueError(f"bit fuori range (0..7): {bit}")
                if value:
                    new_byte = existing_byte | (1 << bit)
                else:
                    new_byte = existing_byte & ~(1 << bit)
                raw = bytes([new_byte])
            elif dt == "B":
                raw = int(value).to_bytes(1, byteorder="big", signed=False)
            elif dt in {"W", "I"}:
                # INT16 signed
                raw = int(value).to_bytes(2, byteorder="big", signed=True)
            elif dt == "D":
                # DWORD unsigned 32
                raw = int(value).to_bytes(4, byteorder="big", signed=False)
            elif dt == "R":
                # REAL float32
                raw = struct.pack(">f", float(value))
            else:
                raise ValueError(f"Tipo non supportato: {dtype}")
            self._client.write_area(area, db, byte, raw)
        except Exception:  # pragma: no cover - connection/parsing errors
            logging.exception("Failed to write address %s", address)

    def read_all(self) -> Dict[str, Any]:
        """Read all configured items from the PLC.

        Each stored address is expected to use the S7 DB notation, e.g.::

            DB1.DBX0.0   # bool
            DB1.DBW2     # 16-bit int (signed)
            DB1.DBD4     # 32-bit dword (unsigned)  or  DB1.DBR4 / DB1.R4 for REAL

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
                size = {
                    "X": 1,  # indirizzabile a byte
                    "B": 1,
                    "W": 2,  # word 16-bit
                    "I": 2,  # int16 signed
                    "D": 4,  # dword 32-bit unsigned
                    "R": 4,  # real 32-bit
                }[dtype]
                area = snap7.type.Areas.DB if snap7 is not None else 0
                raw = self._client.read_area(area, db, byte, size)

                if dtype == "X":
                    result[topic] = bool(raw[0] & (1 << bit))
                elif dtype == "B":
                    result[topic] = raw[0]
                elif dtype in {"W", "I"}:
                    result[topic] = int.from_bytes(raw, byteorder="big", signed=True)
                elif dtype == "D":
                    result[topic] = int.from_bytes(raw, byteorder="big", signed=False)
                elif dtype == "R":
                    result[topic] = struct.unpack(">f", raw)[0]
                else:
                    raise ValueError(f"Tipo non supportato: {dtype}")
            except Exception:  # pragma: no cover - connection/parsing errors
                logging.exception("Failed to read address %s", address)
        return result

    @staticmethod
    def _parse_address(address: str) -> tuple[int, str, int, int]:
        """Parse an S7 DB address.

        Returns a tuple of ``(db_number, data_type, byte_offset, bit_offset)``.
        ``bit_offset`` is zero when not used.

        Tipi supportati (e alias):
          X   (bit)                       -> DBX
          B   (byte)                      -> DBB
          W/I (word/int16 signed)         -> DBW / DBI
          D   (dword uint32)              -> DBD / D BW alias DW
          R   (real float32)              -> DBR / DR
        """

        m = re.fullmatch(
            r"DB(\d+)\.(?:DB)?(X|B|W|DW|D|I|DI|R|DR)(\d+)(?:\.(\d+))?",
            address.upper()
        )
        if not m:
            raise ValueError(f"Unsupported address format: {address}")

        db = int(m.group(1))
        dtype = m.group(2)
        byte = int(m.group(3))
        bit = int(m.group(4) or 0)

        # Normalizza alias
        if dtype in {"DW"}:
            dtype = "D"
        elif dtype in {"DI"}:
            dtype = "I"
        elif dtype in {"DR"}:
            dtype = "R"

        return db, dtype, byte, bit
