import time, logging
from typing import Any, Callable


class Attribute:
    """Represents a single value on the PLC exposed via MQTT."""

    def __init__(self, plc, mqtt, name: str, plc_type: str, mqtt_device_topic: str, retain_messages: bool = False):
        self.plc_handler = plc
        self.mqtt_handler = mqtt
        self.name = name
        self.type = plc_type
        self.full_mqtt_topic = f"{mqtt_device_topic}/{name}"
        self.retain_messages = bool(retain_messages)

        self.plc_address: str | None = None
        self.plc_set_address: str | None = None

        self.publish_to_mqtt = True
        self.write_to_plc = True
        self.is_internal = False
        self.boolean_inverted = False
        self.round_value = True
        self.write_back = False

        self.last_update = 0.0
        self.last_value: Any = None
        self.update_interval = 0  # ms

        if self.write_to_plc:
            self.mqtt_handler.subscribe(self.full_mqtt_topic + "/set")

        self.subscribe_plc_updates()

    def subscribe_plc_updates(self) -> None:
        if self.plc_address:
            self.plc_handler.add_item(self.full_mqtt_topic, self.plc_address)

    def set_RW(self, mode: str) -> None:
        mode = mode.lower()
        if mode == "r":
            self.write_to_plc = False
            self.publish_to_mqtt = True
        elif mode == "w":
            self.write_to_plc = True
            self.publish_to_mqtt = False
        elif mode == "i":
            self.write_to_plc = True
            self.publish_to_mqtt = False
            self.is_internal = True
        else:
            self.write_to_plc = True
            self.publish_to_mqtt = True

    # Incoming data from PLC
    def rec_s7_data(self, data: Any) -> None:
        if not self.publish_to_mqtt:
            return
        if self.type == "REAL" and self.round_value:
            try:
                data = round(float(data), 3)
            except Exception:
                pass
        if self.type == "X" and self.boolean_inverted:
            data = not bool(data)
        now = time.time() * 1000
        should_update = False
        if self.update_interval:
            should_update = (now - self.last_update) > self.update_interval
        else:
            should_update = data != self.last_value
        if should_update:
            self.last_value = data
            self.last_update = now
            self.mqtt_handler.publish(self.full_mqtt_topic, str(data), retain=self.retain_messages)
            if self.write_back:
                if data == getattr(self, "last_set_data", None):
                    self.last_set_data = None
                else:
                    self.write_to_plc_fn(data)

    # Incoming data from MQTT
    def rec_mqtt_data(self, data: str, cb: Callable[[Any], None] | None = None) -> None:
        res = self.format_message(data, self.type)
        print(f"DEBUG: input={data}, type={self.type}, res={res}")
        if res[0] == 0:
            logging.warning("OK")
            self.write_to_plc_fn(res[1])
            if cb:
                cb(None)
        else:
            logging.warning("Error")
            if cb:
                cb("Incorrect formatting")

    def write_to_plc_fn(self, value: Any) -> None:
        self.last_set_data = value
        self.plc_handler.write_item(self.full_mqtt_topic, value)
        logging.warning("Write:", value, self.full_mqtt_topic)

    def format_message(self, msg: str, plc_type: str, no_debug_out: bool = True):
        """
        Converte una stringa 'msg' nel valore Python corretto in base al tipo PLC.
        Ritorna:
        [0, value]  -> ok
        [-2]        -> parsing/valore non valido
        [-1]        -> tipo non supportato
        """

        def _parse_bool(s: str):
            s = s.strip().lower()
            truthy = {"true", "1", "on", "yes", "y", "si", "s"}
            falsy  = {"false", "0", "off", "no", "n"}
            if s in truthy:
                return True
            if s in falsy:
                return False
            return None

        # Normalizza tipo con alias comuni
        t = (plc_type or "").strip().upper()
        alias_map = {
            "BOOL": "X",
            "BYTE": "B",
            "WORD": "W",
            "INT":  "I",
            "DWORD":"D",
            "REAL": "R",
        }
        t = alias_map.get(t, t)  # mappa alias → tipo base

        # Pulisci msg
        s = (msg or "").strip()

        # Tipi supportati: X, B, W/I, D, R
        if t == "X":
            b = _parse_bool(s)
            if b is None:
                return [-2]
            return [0, b]

        if t == "B":
            try:
                v = int(s, 0)  # supporta "255", "0xff"
            except ValueError:
                return [-2]
            if not (0 <= v <= 255):
                return [-2]
            return [0, v]

        if t in {"W", "I"}:
            try:
                v = int(s, 0)
            except ValueError:
                return [-2]
            if not (-32768 <= v <= 32767):
                return [-2]
            return [0, v]

        if t == "D":
            try:
                # uint32
                v = int(s, 0)
            except ValueError:
                return [-2]
            if not (0 <= v <= 0xFFFFFFFF):
                return [-2]
            return [0, v]

        if t == "R":
            # accetta virgola decimale
            s2 = s.replace(",", ".")
            try:
                v = float(s2)
            except ValueError:
                return [-2]
            return [0, v]

        return [-1]