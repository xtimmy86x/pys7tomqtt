import asyncio, logging
import yaml
from typing import Dict

from .mqtt_client import MqttClient
from .plc_client import PlcClient
from .device_factory import device_factory

def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def mqtt_message_factory(devices):
    def mqtt_message(topic: str, payload: str) -> None:
        parts = topic.split('/')
        if len(parts) < 3:
            return
        device = devices.get(parts[1])
        if device:
            device.rec_mqtt_data(parts[2], payload)
    return mqtt_message


async def main(config_path: str = "config.yaml") -> None:
    cfg = load_config(config_path)

    devices: Dict[str, object] = {}

    mqtt = MqttClient(cfg.get("mqtt", {}), message_callback=mqtt_message_factory(devices))
    plc = PlcClient(cfg.get("plc", {}))
    ha = cfg.get("ha", {})

    for dev_cfg in cfg.get("devices", []):
        dev = device_factory(devices, plc, mqtt, dev_cfg, cfg.get("mqtt_base", "s7"), cfg.get("retain_messages", False), ha.get("discovery_topic", "hatest"), ha.get("discovery_retain", False))
        devices[dev.mqtt_name] = dev
        if ha.get("discovery", False):
            dev.send_discover_msg()

    update_time = cfg.get("update_time", 1)

    while True:
        readings = plc.read_all()
        for topic, value in readings.items():
            parts = topic.split('/')
            if len(parts) < 3:
                continue
            device = devices.get(parts[1])
            if device:
                device.rec_s7_data(parts[2], value)
        await asyncio.sleep(update_time)


if __name__ == "__main__":
    # asyncio.run(main())
    # logging.basicConfig(level=logging.INFO) # Uncomment for debugging 
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
