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
        if res[0] == 0:
            self.write_to_plc_fn(res[1])
            if cb:
                cb(None)
        else:
            if cb:
                cb("Incorrect formatting")

    def write_to_plc_fn(self, value: Any) -> None:
        self.last_set_data = value
        self.plc_handler.write_item(self.full_mqtt_topic, value)

    def format_message(self, msg: str, plc_type: str, no_debug_out: bool = True):
        if plc_type == "X":
            if msg == "true":
                return [0, True]
            if msg == "false":
                return [0, False]
            return [-2]
        if plc_type == "BYTE":
            try:
                return [0, int(msg)]
            except ValueError:
                return [-2]
        if plc_type == "REAL":
            try:
                return [0, float(msg)]
            except ValueError:
                return [-2]
        return [-1]