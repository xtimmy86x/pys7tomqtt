import json
import re
from typing import Dict, Any

from .attribute import Attribute


class Device:
    """Base class for devices containing multiple attributes."""

    def __init__(self, plc, mqtt, config: dict):
        self.plc_handler = plc
        self.mqtt_handler = mqtt
        self.name = config.get("name", "unnamed device")
        self.type = config["type"].lower()
        self.discovery_topic = config.get("discovery_prefix", "homeassistant")
        self.discovery_retain = config.get("discovery_retain", False)
        self.retain_messages = config.get("retain_messages", False)

        self.mqtt_name = config.get("mqtt", self.name.lower().replace(" ", "-").replace("/", "-"))
        base = config.get("mqtt_base", "s7")
        self.full_mqtt_topic = f"{base}/{self.mqtt_name}"

        self.attributes: Dict[str, Attribute] = {}

    def create_attribute(self, config: Any, required_type: str, name: str) -> None:
        attr = Attribute(self.plc_handler, self.mqtt_handler, name, required_type, self.full_mqtt_topic, self.retain_messages)
        if isinstance(config, dict):
            attr.plc_address = config.get("plc")
            attr.plc_set_address = config.get("set_plc")
            if config.get("rw"):
                attr.set_RW(config["rw"])
            if config.get("update_interval"):
                attr.update_interval = config["update_interval"]
            if config.get("inverted"):
                attr.boolean_inverted = config["inverted"]
            if config.get("unit_of_measurement"):
                attr.unit_of_measurement = config["unit_of_measurement"]
            if config.get("write_back"):
                attr.write_back = config["write_back"]
        else:
            attr.plc_address = config
        attr.subscribe_plc_updates()

        # check type from address
        if attr.plc_address:
            offset = attr.plc_address.split(',')
            if len(offset) > 1:
                params = re.findall(r'(\d+|\D+)', offset[1])
                plc_type = params[0]
                if required_type and plc_type != required_type:
                    return
                attr.type = plc_type
        self.attributes[name] = attr

    def send_discover_msg(self, info: Dict[str, Any] | None = None) -> None:
        info = info or {}
        topic = f"{self.discovery_topic}/{self.type}/s7-connector/{self.mqtt_name}/config"
        info["uniq_id"] = f"s7-{self.mqtt_name}"
        self.mqtt_handler.publish(topic, json.dumps(info), retain=self.discovery_retain)

    def rec_s7_data(self, attr: str, data: Any) -> None:
        if attr in self.attributes:
            self.attributes[attr].rec_s7_data(data)

    def rec_mqtt_data(self, attr: str, data: str) -> None:
        if attr in self.attributes:
            self.attributes[attr].rec_mqtt_data(data)

    def get_plc_address(self, attr: str):
        a = self.attributes.get(attr)
        return a.plc_address if a else None

    def get_plc_set_address(self, attr: str):
        a = self.attributes.get(attr)
        if not a:
            return None
        return a.plc_set_address or a.plc_address