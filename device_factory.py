from typing import Dict

from .device import Device
from .devices import LightDevice, SensorDevice


def device_factory(devices: Dict[str, Device], plc, mqtt, config: dict, mqtt_base: str, retain_messages: bool) -> Device:
    """Create a new device instance based on the configuration.

    The implementation mirrors the behaviour of the original Node.js
    `deviceFactory` by ensuring unique MQTT topic names and propagating common
    configuration flags.  Only a subset of device types is implemented; unknown
    types fall back to the generic :class:`Device`.
    """
    type_lower = config["type"].lower()
    name = config.get("name", "unnamed device")
    mqtt_name = config.get("mqtt", name.lower().replace(" ", "-").replace("/", "-"))

    index = 1
    new_mqtt_name = mqtt_name
    while new_mqtt_name in devices:
        new_mqtt_name = f"{mqtt_name}-{index}"
        index += 1

    config["name"] = name
    config["mqtt"] = new_mqtt_name
    config["mqtt_base"] = mqtt_base
    config["retain_messages"] = retain_messages
    
    if type_lower == "light":
        device = LightDevice(plc, mqtt, config)
    elif type_lower == "switch":
        device = LightDevice(plc, mqtt, config)
    elif type_lower == "sensor":
        device = SensorDevice(plc, mqtt, config)
    else:
        device = Device(plc, mqtt, config)
    return device