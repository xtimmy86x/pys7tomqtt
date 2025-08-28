import json
import re
from typing import Dict, Any

from .attribute import Attribute
from .utils import Utils

class Device:
    """Base class for devices containing multiple attributes."""

    def __init__(self, plc, mqtt, config: dict):
        self.plc_handler = plc
        self.mqtt_handler = mqtt
        self.name = config.get("name", "unnamed device")
        self.type = config["type"].lower()
        self.discovery_topic = config.get("discovery_topic", "testha")
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
            offset = attr.plc_address.split('.')
            test = Utils._parse_address(self, attr.plc_address)[1]
            if len(offset) > 10:
                token = offset[1].strip().upper()  # es: "DB11.X1.0", "DB11.I1", "DB11.DBX1.0", "WORD 4"
                # rimuovi eventuale prefisso "DB<number>."
                token = re.sub(r'^DB\d+\.', '', token)  # "DB11.X1.0" -> "X1.0", "DB11.I1" -> "I1"
                # prendi la prima "parola" alfabetica (DBX, X, I, B, W, D, WORD, DWORD, BOOL, INT, ecc.)
                m = re.match(r'[A-Z]+', token)
                if not m:
                    # niente prefisso alfabetico → non riesco a dedurre il tipo
                    return
                head = m.group(0)  # es: "X", "I", "DBX", "WORD", "B", "W", "D", "INT", "DWORD", ...
                # mapping completo
                type_map = {
                    'BOOL': 'X',
                    'DBX' : 'X',
                    'X'   : 'X',

                    'BYTE': 'B',
                    'DBB' : 'B',
                    'B'   : 'B',

                    'WORD': 'W',
                    'DBW' : 'W',
                    'W'   : 'W',
                    'INT' : 'I',   # INT16
                    'I'   : 'I',   # shorthand comune per INT → Word

                    'DWORD': 'D',
                    'DBD'  : 'D',
                    'D'    : 'D',
                    'DINT' : 'D',  # INT32
                    'REAL' : 'D',  # opzionale: trattalo come D se lo gestisci insieme a DWord
                    # aggiungi qui altre sigle se nel tuo progetto ne hai
                }
            if len(offset) > 1:
                plc_type = test #type_map.get(head)

                if not plc_type:
                    
                    # fallback: se è qualcosa tipo "DB?" prendi ultima lettera
                    if head.startswith('DB') and len(head) >= 3:
                        plc_type = head[-1]  # DBX->X, DBW->W, ecc.
                    else:
                        return  # tipo non riconosciuto
                if required_type and plc_type != required_type:
                    return
                
                attr.type = plc_type
        self.attributes[name] = attr


    def send_discover_msg(self, info: Dict[str, Any] | None = None) -> None:
        info = info or {}
        topic = f"{self.discovery_topic}/{self.type}/s7-connector/{self.mqtt_name}/config"
        info["uniq_id"] = f"s7-{self.mqtt_name}"
        info["name"] = self.name
        info["command_topic"] = f"{self.full_mqtt_topic}/state/set"
        info["state_topic"] = f"{self.full_mqtt_topic}/state"
        info["state_on"] = "ON"
        info["state_off"] = "OFF"
        info["payload_on"] = "ON"
        info["payload_off"] = "OFF"
        info["availability_topic"] = f"{self.full_mqtt_topic}/availability"
        info["payload_available"] = "online"
        info["payload_not_available"] = "offline"

            
        if self.attributes:
            info["json_attributes_topic"] = f"{self.full_mqtt_topic}/attributes"
            info["json_attributes_template"] = "{{ value_json | tojson }}"
            attr_info = {}
            for attr_name, attr in self.attributes.items():
                info["unit_of_measurement"] = attr.unit_of_measurement
                attr_info[attr_name] = {
                    "plc_address": attr.plc_address,
                    "set_plc_address": (attr.plc_set_address or attr.plc_address),
                    "type": attr.type,
                }
            info["attributes_info"] = attr_info

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
    